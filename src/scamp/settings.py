"""
Module containing the main settings classes: :class:`PlaybackSettings`, :class:`QuantizationSettings`, and
:class:`EngravingSettings`, as well as :class:`TempoSettings` and :class:`GlissandiSettings`, which are part of
:class:`EngravingSettings`. A module-level instance for each (:code:`playback_settings`, :code:`quantization_settings`,
and :code:`engraving_settings`) is loaded from JSON configuration files within within the settings directory of the
scamp package. These instances are part of the global scamp namespace, and contain scamp's default configuration.
"""

#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  This file is part of SCAMP (Suite for Computer-Assisted Music in Python)                      #
#  Copyright © 2020 Marc Evanstein <marc@marcevanstein.com>.                                     #
#                                                                                                #
#  This program is free software: you can redistribute it and/or modify it under the terms of    #
#  the GNU General Public License as published by the Free Software Foundation, either version   #
#  3 of the License, or (at your option) any later version.                                      #
#                                                                                                #
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;     #
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     #
#  See the GNU General Public License for more details.                                          #
#                                                                                                #
#  You should have received a copy of the GNU General Public License along with this program.    #
#  If not, see <http://www.gnu.org/licenses/>.                                                   #
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
from __future__ import annotations
import os
import shutil
import sys
from dataclasses import dataclass, field, fields, MISSING
from .utilities import resolve_path, SavesToJSON, first_run_notice
from .playback_adjustments import NotePlaybackAdjustment
from expenvelope.envelope import Envelope
from . import spelling
import logging
import json
import platform
import subprocess


class _ScampSettings(SavesToJSON):

    """
    Base class for scamp settings classes. Subclasses are dataclasses (decorated with
    ``@dataclass(repr=False, eq=False)``) whose field declarations are the single source of truth
    for both the schema and the factory defaults. The auto-generated dataclass ``__init__``
    handles construction (use kwargs to override individual fields); ``_from_dict`` is the
    entry point for loading from JSON, with migration handling.
    """

    _settings_name = "Settings"
    _json_path = None
    _is_root_setting = False

    # Subclasses can declare lazily-resolved fields here. Each entry maps a field name to a
    # resolver function `(self) -> value`; the resolver runs the first time the attribute is
    # read while the stored value is None, and the result is cached on the instance. Names
    # listed in `_persist_after_resolve` also get written to the JSON file after resolution
    # so subsequent processes don't pay the resolution cost again.
    _resolvers: dict = {}
    _persist_after_resolve: set = set()

    @classmethod
    def _factory_default(cls, key):
        """Fresh factory default value for a single field, calling the field's default_factory if any."""
        f = cls.__dataclass_fields__[key]
        return f.default_factory() if f.default_factory is not MISSING else f.default

    def __post_init__(self):
        # The dataclass-generated __init__ has just set every field. For resolvable fields
        # whose value is None, delete the instance attribute so __getattr__ fires on first
        # read and triggers the resolver. (The class itself has no attribute for these
        # fields — see the default_factory comment on the field declarations — so once the
        # instance attr is gone, lookup misses and falls into __getattr__.)
        for name in type(self)._resolvers:
            if self.__dict__.get(name) is None:
                del self.__dict__[name]

    def __getattr__(self, name):
        # Only fires when normal lookup misses (attribute not in instance __dict__ and not on
        # the class). For resolvable fields we leave the attribute unset until first access.
        resolvers = type(self)._resolvers
        if name in resolvers:
            value = resolvers[name](self)
            object.__setattr__(self, name, value)
            if name in type(self)._persist_after_resolve and self._is_root_setting:
                self.make_persistent()
            return value
        raise AttributeError(name)

    def restore_factory_defaults(self, persist=False) -> None:
        """
        Restores settings back to their "factory defaults" (the defaults when SCAMP was installed).
        Unless the `persist` argument is set, this is temporary to the running of the current script.

        :param persist: if True, rewrites the JSON file from which defaults are loaded, meaning that this reset will
            persist to the running of scripts in the future.
        """
        resolvers = type(self)._resolvers
        for f in fields(self):
            value = self._factory_default(f.name)
            if value is None and f.name in resolvers:
                # Leave unset so the next read re-runs the resolver.
                self.__dict__.pop(f.name, None)
            else:
                object.__setattr__(self, f.name, value)
        if persist:
            self.make_persistent()

    def make_persistent(self) -> None:
        """
        Rewrites the JSON file from which settings are loaded, meaning that this reset will persist to the running of
        scripts in the future.
        """
        self.save_to_json(resolve_path(self._json_path))

    @classmethod
    def factory_default(cls):
        """
        Returns a factory default version of this settings object.
        """
        return cls()

    def _to_dict(self):
        # For resolvable fields that haven't been resolved yet, write None to JSON rather
        # than triggering resolution as a side effect of saving.
        resolvers = type(self)._resolvers
        out = {}
        for f in fields(self):
            if f.name in resolvers and f.name not in self.__dict__:
                out[f.name] = None
            else:
                out[f.name] = getattr(self, f.name)
        return out

    @classmethod
    def _migrate_settings_dict(cls, settings_dict, suppress_warnings=False):
        """
        Translate a raw on-disk settings dict into kwargs for ``cls.__init__``, applying
        schema migrations: drop unexpected keys, fill missing keys from field defaults
        (by omitting them so auto-init uses the default), and translate the legacy
        ``"auto"`` sentinel to ``None`` for resolvable fields. Returns
        ``(kwargs, rewrite_file)`` where ``rewrite_file`` is True if any migration
        happened and the JSON should be re-saved.
        """
        field_names = {f.name for f in fields(cls)}
        resolvers = cls._resolvers
        rewrite_file = False
        kwargs = {}

        json_filename = cls._json_path.split("/")[-1] if cls._json_path is not None else "settings"

        for key, value in settings_dict.items():
            if key not in field_names:
                if not suppress_warnings:
                    logging.warning(f"Removing unexpected key \"{key}\" in {json_filename}.")
                rewrite_file = True
                continue
            # Treat the legacy "auto" sentinel as equivalent to None for resolvable fields,
            # so old persisted JSON files trigger the resolver on the next read.
            if key in resolvers and value == "auto":
                value = None
                rewrite_file = True
            kwargs[key] = value

        for name in field_names - kwargs.keys():
            if not suppress_warnings:
                logging.warning(f"Key \"{name}\" was not found in {json_filename}, and will be added.")
            rewrite_file = True
            # Don't put it in kwargs; the auto-init will use the field's default.

        return kwargs, rewrite_file

    @classmethod
    def _from_dict(cls, settings_dict, suppress_warnings=False):
        """
        Construct a settings instance from a dict (typically loaded from JSON), migrating
        the dict's schema first (see ``_migrate_settings_dict``) and re-saving the JSON
        file if migration occurred.
        """
        kwargs, rewrite_file = cls._migrate_settings_dict(settings_dict, suppress_warnings)
        instance = cls(**kwargs)
        if rewrite_file and cls._is_root_setting:
            instance.make_persistent()
        return instance

    @classmethod
    def load(cls):
        """
        Loads and instance of this settings object from its corresponding JSON file. If no such file exists, or it is
        corrupted in some way, then this creates a fresh JSON file there. This doesn't work with settings that are
        nested within other settings (like GlissandiSettings), since they do not have corresponding JSON files,
        """
        assert cls._is_root_setting, "Cannot load a non-root setting automatically."
        try:
            return cls.load_from_json(resolve_path(cls._json_path))
        except FileNotFoundError:
            logging.warning("{} not found; generating defaults. "
                            "(This is normal on first import.)".format(cls._settings_name))
            factory_defaults = cls.factory_default()
            factory_defaults.make_persistent()
            return factory_defaults
        except (TypeError, ValueError, json.decoder.JSONDecodeError):
            logging.warning(f"Error loading {cls._settings_name.lower()}; falling back to defaults. (This could be due "
                            f"to a change in SCAMP version.)")
            return cls.factory_default()

    def open_json_file(self, *command_and_flags):
        """
        Open the JSON file for these settings.

        :param command_and_flags: the command-line tool with which to open the file, and any associated flags.
            Defaults to a platform-specific generic open command.
        """
        platform_system = platform.system().lower()
        command_and_flags = list(command_and_flags) if len(command_and_flags) > 0 \
            else ["xdg-open"] if platform_system == "linux" \
            else ["open"] if platform_system == "darwin" \
            else ["notepad"] if platform_system == "windows" \
            else None
        if command_and_flags is None:
            raise ValueError("Unrecognized platform {}".format(platform_system))
        subprocess.call(command_and_flags + [resolve_path(self._json_path)])

    @staticmethod
    def _validate_attribute(key, value):
        return value

    def __setattr__(self, key, value):
        object.__setattr__(self, key, self._validate_attribute(key, value))


@dataclass(repr=False, eq=False)
class PlaybackSettings(_ScampSettings):

    """
    Namespace containing the settings relevant to playback implementation and adjustments.

    :param settings_dict: dictionary from which to set all settings attributes
    :ivar named_soundfonts: Dictionary mapping names of frequently-used soundfonts to their file paths
    :ivar default_soundfont: Soundfont (by name or path) to default to in playback
    :ivar default_audio_driver: Name of the audio driver use for soundfont playback by default. If "auto", we test to
        see what audio driver will work, and replace this value with that driver.
    :ivar default_max_soundfont_pitch_bend: When playing back with soundfonts, instruments will be immediately set
        to use this value for the maximum pitch bend. (Makes sense to set this to a large value for maximum flexibility)
    :ivar default_max_streaming_midi_pitch_bend: When playing back with a midi stream to an external
        synthesizer/program, instruments will be immediately set to use this value for the maximum pitch bend. (Makes
        sense probably to leave this at the MIDI default of 2 semitones, in case the receiving device doesn't listen
        to messages that reset the pitch bend range.)
    :ivar soundfont_volume_to_velocity_curve: an :class:`~expenvelope.envelope.Envelope` defining how volume values get
        mapped to MIDI velocities in soundfont-based playback. The default maps the range 0-1 to the range 0-127, but
        with some non-linear shaping towards higher velocity values. This is because, for some reason, soundfont
        playback is almost inaudible low velocities.
    :ivar streaming_midi_volume_to_velocity_curve: same as ``soundfont_volume_to_velocity_curve``, but for streaming
        MIDI playback. This defaults to a linear mapping from 0-1 to 0-127.
    :ivar osc_message_addresses: Dictionary mapping the different kinds of playback messages to the OSC messages
        prefixes we will use for them. For instance, if you want start note messages to use "note_on", set the
        osc_message_addresses["start_note"] = "note_on", and all OSC messages starting a note will come out as
        [instrument name]/note_on/
    :ivar adjustments: a dictionary defining how playback should be altered in response to different
        articulations/notations/etc.
    :ivar try_system_fluidsynth_first: if True, always tries the system copy of the libfluidsynth shared library
        first before falling back to the one embedded in the scamp package. Defaults to True on Linux (where a
        package-managed fluidsynth is usually better integrated with the host audio stack) and False on Mac/Windows.
    :ivar use_bundled_pyfluidsynth: if True (the default everywhere), use scamp's bundled copy of the pyfluidsynth
        Python wrapper. The bundled wrapper can dlopen either the system or the bundled libfluidsynth (controlled by
        ``try_system_fluidsynth_first``). Set to False to use a separately-installed pyfluidsynth pip package instead.
    :ivar resize_parameter_envelopes: one of "never", "lists", and "always". This determines whether or not parameter
        envelopes are resized to the length of the note. The default value of "lists" does this resizing only when the
        envelope was created indirectly by passing a list to the parameter.
    """

    named_soundfonts: dict = field(default_factory=lambda: {"general_midi": "Merlin.sf2"})
    soundfont_search_paths: list = field(default_factory=lambda: ["%PKG/soundfonts"])
    default_soundfont: str = "general_midi"
    # Resolved lazily on first read by probing each backend (see ``_resolvers`` below).
    # ``default_factory=lambda: None`` (rather than ``= None``) is deliberate: a plain
    # ``= None`` default puts a class-level attribute equal to None on the class, which
    # would mask ``__getattr__`` even after we delete the instance attr. ``default_factory``
    # leaves no class attribute behind, so once ``__post_init__`` deletes the instance attr
    # the attribute lookup misses entirely and ``__getattr__`` fires the resolver.
    default_audio_driver: str | None = field(default_factory=lambda: None)
    default_max_soundfont_pitch_bend: int = 48
    default_max_streaming_midi_pitch_bend: int = 2
    soundfont_volume_to_velocity_curve: Envelope = field(
        default_factory=lambda: Envelope.from_points((0, 0), (0.1, 40), (1, 127))
    )
    streaming_midi_volume_to_velocity_curve: Envelope = field(
        default_factory=lambda: Envelope.from_points((0, 0), (1, 127))
    )
    osc_message_addresses: dict = field(default_factory=lambda: {
        "start_note": "start_note",
        "end_note": "end_note",
        "change_pitch": "change_pitch",
        "change_volume": "change_volume",
        "change_parameter": "change_parameter",
    })
    adjustments: dict = field(default_factory=lambda: {
        "articulations": {
            "staccato": NotePlaybackAdjustment.scale_params(length=0.5),
            "staccatissimo": NotePlaybackAdjustment.scale_params(length=0.3),
            "tenuto": NotePlaybackAdjustment.scale_params(length=1.2),
            "accent": NotePlaybackAdjustment.scale_params(volume=1.2),
            "marcato": NotePlaybackAdjustment.scale_params(volume=1.5),
        }
    })
    # On Linux, prefer the user's package-managed fluidsynth: it's built
    # against their system's audio stack (PulseAudio/PipeWire/JACK) and
    # almost always works better than the bundled lib for desktop output.
    # On Mac/Windows the bundled lib is well-tested via cibuildwheel and
    # system fluidsynth is rare, so bundled-first is the better default.
    try_system_fluidsynth_first: bool = field(default_factory=lambda: sys.platform == "linux")
    # Always default to the bundled pyfluidsynth wrapper: it knows how to
    # locate scamp's bundled libfluidsynth and is the version we test
    # against. The wrapper itself respects try_system_fluidsynth_first to
    # decide which underlying libfluidsynth to dlopen.
    use_bundled_pyfluidsynth: bool = True
    resize_parameter_envelopes: str = "lists"
    recording_file_path: str | None = None
    recording_time_range: list = field(default_factory=lambda: [0, "inf"])

    _settings_name = "Playback settings"
    _json_path = "%DATA/playbackSettings.json"
    _is_root_setting = True

    _resolvers = {
        "default_audio_driver": lambda self: _resolve_audio_driver(),
    }
    _persist_after_resolve = {"default_audio_driver"}

    def register_named_soundfont(self, name: str, soundfont_path: str) -> None:
        """
        Adds a named soundfont, so that it can be easily referred to in constructing a Session

        :param name: the soundfont name
        :param soundfont_path: the absolute path to the soundfont, staring with a slash, or a relative path that
            gets resolved relative to the soundfonts directory
        """
        self.named_soundfonts[name] = soundfont_path

    def unregister_named_soundfont(self, name: str) -> None:
        """
        Same as above, but removes a named soundfont

        :param name: the default soundfont name to remove
        """
        if name not in self.named_soundfonts:
            logging.warning("Tried to unregister default soundfont '{}', but it didn't exist.".format(name))
            return
        del self.named_soundfonts[name]

    def list_named_soundfonts(self) -> None:
        """
        Prints out a list of all of the named soundfonts and the paths of the soundfont files to which they point.
        """
        for a, b in self.named_soundfonts.items():
            print("{}: {}".format(a, b))

    def set_playback_adjustment(self, note_property: str, adjustment: str | NotePlaybackAdjustment):
        from ._parsing import parse_property_key_and_value, parse_note_playback_adjustment

        key, value = parse_property_key_and_value(note_property)

        if key == "playback_adjustments":
            raise ValueError("Cannot set a playback adjustment for a playback adjustment. That's just silly.")

        if key not in self.adjustments:
            self.adjustments[key] = {}

        if isinstance(adjustment, NotePlaybackAdjustment):
            self.adjustments[key][value] = adjustment
        else:
            self.adjustments[key][value] = parse_note_playback_adjustment(adjustment)

    def get_playback_adjustment(self, note_property: str):
        from ._parsing import parse_property_key_and_value

        key, value = parse_property_key_and_value(note_property)

        if key == "playback_adjustments":
            raise ValueError("Cannot get a playback adjustment for a playback adjustment. That's just silly.")

        try:
            return self.adjustments[key][value]
        except KeyError:
            return None

    @staticmethod
    def _validate_attribute(key, value):
        if key == "resize_parameter_envelopes" and value not in ("lists", "always", "never"):
            fallback = PlaybackSettings._factory_default("resize_parameter_envelopes")
            logging.warning(
                "Invalid value of \"{}\" for glissando control point policy: must be one of: \"lists\", \"always\", or "
                "\"never\". Defaulting to \"{}\".".format(value, fallback)
            )
            return fallback
        return value


@dataclass(repr=False, eq=False)
class QuantizationSettings(_ScampSettings):
    """
    Namespace containing the settings relevant to the quantization of Performances in preparation for Score creation.

    :param settings_dict: dictionary from which to set all settings attributes
    :ivar onset_weighting: float representing how much note start times are weighted compared with note end times and
        tie split points in determining how beats are divided. (All that matters is the relative size of the values.)
    :ivar termination_weighting:  float representing how much note end times are weighted compared with note start times
        and tie split points in determining how beats are divided. (All that matters is the relative size of the
        values.)
    :ivar inner_split_weighting: float representing how much tie split points are weighted compared with note end times
        and note start times in determining how beats are divided. (All that matters is the relative size of the
        values.)
    :ivar max_divisor: int representing the default maximum divisor allowed for a beat
    :ivar max_divisor_indigestibility: float representing the default cap on the indigestibility of beat divisors. (See
        :class:`~scamp.quantization.BeatQuantizationScheme`)
    :ivar simplicity_preference: float representing the default degree of preference for simple beat divisors. (See
        :class:`~scamp.quantization.BeatQuantizationScheme`)
    :ivar default_time_signature: string (e.g. "4/4") representing the default time signature to use when one is not
        specified.
    """

    onset_weighting: float = 1.0
    termination_weighting: float = 0.5
    inner_split_weighting: float = 0.75
    max_divisor: int = 8
    max_divisor_indigestibility: float | None = None
    simplicity_preference: float = 2.0
    default_time_signature: str = "4/4"

    _settings_name = "Quantization settings"
    _json_path = "%DATA/quantizationSettings.json"
    _is_root_setting = True


@dataclass(repr=False, eq=False)
class GlissandiSettings(_ScampSettings):
    """
    Namespace containing the settings relevant to the engraving of glissandi.

    :param settings_dict: dictionary from which to set all settings attributes
    :ivar control_point_policy: Can be either "grace", "split", or "none":

        * if "grace", the rhythm is expressed as simply as possible and they are engraved as headless grace notes
        * if "split", the note is split rhythmically at the control points
        * if "none", control points are ignored

    :ivar consider_non_extrema_control_points: if true, we consider all gliss control points in the engraving process.
        If false, we only consider local extrema (i.e. points where the gliss changes direction).
    :ivar include_end_grace_note: if true, the final pitch reached is expressed as a gliss up to a headless grace note.
    :ivar inner_grace_relevance_threshold: this threshold helps determine which gliss control points are worth
        expressing in notation. The further a control point is from its neighbors, and the further it deviates from
        the linearly interpolated pitch at that point, the higher its relevance score. The relevance score must be
        above this threshold to show up.
    :ivar max_inner_graces_music_xml: integer (probably 1) capping the number of inner grace notes between notes of a
        glissando that we put in when outputting music xml. (Most programs can't even handle 1 appropriately, but
        there's nothing inherently unclear about including more in the XML.)
    """

    control_point_policy: str = "split"
    consider_non_extrema_control_points: bool = True
    include_end_grace_note: bool = True
    inner_grace_relevance_threshold: float = 1.5
    max_inner_graces_music_xml: int = 1
    slur_glisses: bool = True

    _settings_name = "Glissandi settings"
    _json_path = "%DATA/engravingSettings.json"
    _is_root_setting = False

    @staticmethod
    def _validate_attribute(key, value):
        if key == "control_point_policy" and value not in ("grace", "split", "none"):
            fallback = GlissandiSettings._factory_default("control_point_policy")
            logging.warning(
                "Invalid value of \"{}\" for glissando control point policy: must be one of: \"grace\", \"split\", or "
                "\"none\". Defaulting to \"{}\".".format(value, fallback)
            )
            return fallback
        return value


@dataclass(repr=False, eq=False)
class TempoSettings(_ScampSettings):
    """
    Namespace containing the settings relevant to the engraving of tempo changes.

    :param settings_dict: dictionary from which to set all settings attributes
    :ivar guide_mark_resolution: grid that the guide marks are snapped to, in beats. Actual appearance of a guide mark
        depends on `guide_mark_sensitivity`.
    :ivar guide_mark_sensitivity: guide_mark_sensitivity represents how much a tempo has to change proportionally to
        put a guide mark. For instance, if it's 0.1 and the last notated tempo was 60, we'll put a guide mark when the
        tempo reaches 60 +/- 0.1 * 60 = 54 or 66.
    :ivar include_guide_marks: Whether or not to include tempo guide marks, i.e. marks showing the tempo at points
        in between explicit tempo targets.
    :ivar parenthesize_guide_marks: Whether or not to place tempo guide marks in parentheses.
    """

    guide_mark_resolution: float = 0.125
    guide_mark_sensitivity: float = 0.08
    include_guide_marks: bool = True
    parenthesize_guide_marks: bool = True

    _settings_name = "Tempo settings"
    _json_path = "%DATA/engravingSettings.json"
    _is_root_setting = False


@dataclass(repr=False, eq=False)
class EngravingSettings(_ScampSettings):
    """
    Namespace containing the settings relevant to the engraving of scores.

    :param settings_dict: dictionary from which to set all settings attributes
    :ivar allow_duple_tuplets_in_compound_time: There are two ways to express a division of a beat in compound time in
        two: with a duple tuplet or with dotted notes. For instance, half of a beat in 3/8 can be represented as a
        dotted-eighth or an eighth inside of a 2:3 tuplet. If this is set to True, we allow the latter option.
    :ivar max_voices_per_part: integer specifying how many voices we allow in a single staff before creating extra
        staves to accommodate them.
    :ivar max_dots_allowed: integer specifying how many dots we allow a note to have before it's just too many dots.
    :ivar beat_hierarchy_spacing: Should be >= 1. Larger numbers treat the various nested levels of beat subdivision as
        further apart, leading to a greater tendency to show the beat structure rather than combine tie notes into
        fewer pieces.
    :ivar num_divisions_penalty: Ranges from 0 to 1, where 0 treats having multiple tied notes to represent a single
        note event as just as good as having fewer notes, while numbers closer to 1 increasingly favor using fewer
        notes in a tied group.
    :ivar rest_beat_hierarchy_spacing: Same as beat_hierarchy_spacing, but for rests. (We generally want rests to be
        more likely to split.)
    :ivar rest_num_divisions_penalty: Same as num_divisions_penalty, but for rests. (We generally want rests to be less
        inclined to recombine.)
    :ivar articulation_split_protocols: Dictionary mapping articulation names to either "first", "last", "both" or
        "all". When a note has been given a particular articulation during playback, but needs to be engraved as a group
        of tied notes, the question arises: which of those tied pieces should get the articulation? For instance, an
        accent probably wants to be on the first note, since it's an attack, and a staccato dot probably should be on
        the last note, since it's about release. The value "both" will place the articulation on both the first and last
        note, and "all" will place the articulation on every note of the tied group.
    :ivar clefs_by_instrument: Dictionary mapping instrument names to a list of clefs used by those instruments. Instead
        of simply the clef name, a tuple of (clef name, redefined_pitch_center) can be given. This overrides the pitch
        center given in clef_pitch_centers for that clef on that instrument, since clef choice can be idiosyncratic to
        the given instrument. The "DEFAULT" entry is used for instruments not explicitly specified.
    :ivar clef_pitch_centers: Pitch center used when deciding on clef choice. Default is to use the pitch of the center
        line. The clef chosen will be the one whose pitch center is closest to the average pitch.
    :ivar clef_selection_policy: Either "measure-wise", in which case clef can be changed measure by measure if needed,
        or "part-wise", in which case a single clef choice is used for the entire part..
    :ivar default_titles: Title or list of titles from which to choose for a score that has been created without
        specifying a title.
    :ivar default_composers: Name or list of name from which to choose for a score that has been created without
        specifying a composer.
    :ivar default_spelling_policy: the SpellingPolicy to use by default in determining accidentals.
    :ivar ignore_empty_parts: if True, don't bother to include parts in a score if there's nothing in them.
    :ivar glissandi: instance of :class:`GlissandiSettings` specifying how glissandi should be engraved.
    :ivar tempo: instance of :class:`TempoSettings` specifying how tempo changes should be engraved.
    :ivar pad_incomplete_parts: If true, add measures to parts that don't have enough music in them so that they are
        go the full length of the score.
    :ivar music_xml_open_command: Terminal command to run when opening up MusicXML scores. It is easiest to set
        this by calling set_music_xml_application. The value "auto" tries to find an appropriate application
        automatically.
    :ivar show_microtonal_annotations: if True, annotates microtonal pitches with the exact floating-point MIDI pitch
        value that they are intended to represent. (This is useful, since normally the best a notation program can
        do is quarter tones.
    :ivar microtonal_annotation_digits: number of digits after the decimal place to show when showing microtonal
        annotations.
    """

    allow_duple_tuplets_in_compound_time: bool = False
    max_voices_per_part: int = 4
    max_dots_allowed: int = 3
    beat_hierarchy_spacing: float = 2.4
    num_divisions_penalty: float = 0.6
    rest_beat_hierarchy_spacing: float = 20
    rest_num_divisions_penalty: float = 0.2
    articulation_split_protocols: dict = field(default_factory=lambda: {
        "staccato": "last",
        "staccatissimo": "last",
        "marcato": "first",
        "tenuto": "both",
        "accent": "first",
        "default": "all",
    })
    notation_split_protocols: dict = field(default_factory=lambda: {
        "tremolo": "all",
        "tremolo1": "all",
        "tremolo2": "all",
        "tremolo3": "all",
        "tremolo4": "all",
        "tremolo5": "all",
        "tremolo6": "all",
        "tremolo7": "all",
        "tremolo8": "all",
        "fermata": "last",
        "default": "first",
    })
    clefs_by_instrument: dict = field(default_factory=lambda: {
        "piano": ["treble", "bass"],
        "flute": ["treble"],
        "oboe": ["treble"],
        "clarinet": ["treble"],
        "bassoon": [("bass", 59), ("tenor", 66), ("treble", 74)],
        "horn": ["treble"],
        "trumpet": ["treble"],
        "trombone": ["bass", "tenor", "treble"],
        "tuba": ["bass"],
        "guitar": ["treble"],
        "timpani": ["bass"],
        "violin": ["treble"],
        "viola": ["alto", ("treble", 75)],
        "cello": [("bass", 59), ("tenor", 66), ("treble", 74)],
        "bass": ["bass", "treble"],
        "default": ["treble", "bass"],
    })
    clef_pitch_centers: dict = field(default_factory=lambda: {
        "bass": 48,
        "tenor": 57,
        "alto": 60,
        "treble": 71,
        "soprano": 67,
        "mezzo-soprano": 64,
        "baritone": 53,
    })
    clef_selection_policy: str = "measure-wise"
    default_titles: list | str | None = field(default_factory=lambda: [
        "On the Code Again", "The Long and Winding Code", "Code To Joy",
        "Take Me Home, Country Codes", "Thunder Code", "Code to Nowhere",
        "Goodbye Yellow Brick Code", "Hit the Code, Jack",
    ])
    default_composers: list | str | None = field(default_factory=lambda: [
        "HTMLvis", "Rustin Beiber", "Javan Morrison", "Sia++",
        "The Rubytles", "CSStiny's Child", "Perl Jam", "PHPrince",
    ])
    default_spelling_policy: spelling.SpellingPolicy = field(
        default_factory=lambda: spelling.SpellingPolicy.from_string("C")
    )
    ignore_empty_parts: bool = True
    glissandi: GlissandiSettings = field(default_factory=GlissandiSettings)
    tempo: TempoSettings = field(default_factory=TempoSettings)
    pad_incomplete_parts: bool = True
    # Resolved lazily on first read from the platform's generic file-open command
    # (xdg-open / open / start). Override via ``set_music_xml_application``. See the
    # ``default_audio_driver`` field on PlaybackSettings for why we use
    # ``default_factory=lambda: None`` instead of ``= None``.
    music_xml_open_command: str | None = field(default_factory=lambda: None)
    show_microtonal_annotations: bool = False
    microtonal_annotation_digits: int = 2
    export_note_velocities_to_xml: bool = False
    # Resolved lazily on first read by searching ``lilypond_search_paths``. See the
    # ``default_audio_driver`` field on PlaybackSettings for the default_factory rationale.
    lilypond_dir: str | None = field(default_factory=lambda: None)
    lilypond_search_paths: dict = field(default_factory=lambda: {
        "Darwin": ["/Applications", "~/Applications", "/usr/local/bin", "/opt/homebrew/bin"],
        "Windows": [r"C:\Program Files (x86)", r"C:\Program Files"],
    })

    _settings_name = "Engraving settings"
    _json_path = "%DATA/engravingSettings.json"
    _is_root_setting = True

    _resolvers = {
        "music_xml_open_command": lambda self: _resolve_music_xml_open_command(),
        "lilypond_dir": lambda self: _resolve_lilypond_dir(),
    }
    _persist_after_resolve = {"lilypond_dir"}

    def set_music_xml_application(self, application_name: str = None, persist: bool = False) -> None:
        """
        Sets the application to use when opening generated MusicXML scores

        :param application_name: name of the application to use. If None, defaults to a generic file open command.
        :param persist: if True, also write the change to the engraving settings JSON so it survives across processes.
        """
        platform_system = platform.system().lower()
        if platform_system == "linux":
            # generic open command on linux is "xdg-open"
            self.music_xml_open_command = application_name if application_name is not None else "xdg-open"
        elif platform_system == "darwin":
            # generic open command on mac is "open"
            self.music_xml_open_command = "open -a {}".format(application_name) \
                if application_name is not None else "open"
        elif platform_system == "windows":
            # generic open command on windows is "start"
            self.music_xml_open_command = "cmd.exe /c start {}".format(application_name) \
                if application_name is not None else "cmd.exe /c start"
        else:
            logging.warning("Cannot run \"show_xml\" on unrecognized platform {}".format(platform_system))
            return
        if persist:
            self.make_persistent()

    def get_default_title(self) -> str | None:
        """Grabs one of the default score titles."""
        if isinstance(self.default_titles, list):
            import random
            return random.choice(self.default_titles)
        elif isinstance(self.default_titles, str):
            return self.default_titles
        else:
            return None

    def get_default_composer(self) -> str | None:
        """Grabs one of the default composer names."""
        if isinstance(self.default_composers, list):
            import random
            return random.choice(self.default_composers)
        elif isinstance(self.default_composers, str):
            return self.default_composers
        else:
            return None

    def _validate_attribute(self, key, value):
        if key == "max_voices_per_part" and not (isinstance(value, int) and 1 <= value <= 4):
            fallback = EngravingSettings._factory_default("max_voices_per_part")
            logging.warning("Invalid value \"{}\" for max_voices_per_part: must be an integer from 1 to 4. defaulting "
                            "to {}".format(value, fallback))
            return fallback
        elif key == "default_composers" and not isinstance(value, (list, str, type(None))):
            logging.warning("Default composers not understood: must be a list, string, or None. "
                            "Falling back to defaults.")
            return EngravingSettings._factory_default("default_composers")
        elif key == "default_titles" and not isinstance(value, (list, str, type(None))):
            logging.warning("Default titles not understood: must be a list, string, or None. Falling back to defaults.")
            return EngravingSettings._factory_default("default_titles")
        elif key == "clef_selection_policy" and value not in ["measure-wise", "part-wise"]:
            logging.warning("Clef selection policy must be either \"measure-wise\" or \"part-wise\"."
                            "Falling back to defaults.")
            return EngravingSettings._factory_default("clef_selection_policy")
        return value


# ---------------------------------------------------------------------------
# Resolvers for lazy ("auto") settings — invoked from _ScampSettings.__getattr__
# the first time the corresponding field is read. Imports are deferred to call
# time to avoid circular imports (the dependency probes live in _dependencies,
# which itself imports this module).
# ---------------------------------------------------------------------------

def _resolve_audio_driver():
    from ._dependencies import probe_audio_driver
    return probe_audio_driver()


def _resolve_music_xml_open_command():
    platform_system = platform.system().lower()
    if platform_system == "linux":
        return "xdg-open"
    if platform_system == "darwin":
        return "open"
    if platform_system == "windows":
        return "cmd.exe /c start"
    logging.warning("Cannot run \"show_xml\" on unrecognized platform {}".format(platform_system))
    return None


def _resolve_lilypond_dir():
    from ._dependencies import find_lilypond
    return find_lilypond()


_factory_lilypond_template_path = os.path.join(resolve_path("%PKG/lilypond"), "scamp_template.ly")
lilypond_template_path = resolve_path("%DATA/scamp_lilypond_template.ly")

if not os.path.exists(resolve_path(lilypond_template_path)):
    first_run_notice(f"Installing lilypond template file at {lilypond_template_path} (this is normal on first import).")
    try:
        shutil.copy(_factory_lilypond_template_path, lilypond_template_path)
    except FileNotFoundError:
        logging.warning(f"Could not find internal lilypond template file. LilyPond output may cause errors.")

#: Instance of :class:`~scamp.settings.PlaybackSettings` containing the actual playback defaults to be consulted
playback_settings: PlaybackSettings = PlaybackSettings.load()
#: Instance of :class:`~scamp.settings.QuantizationSettings` containing the actual quantization defaults to be consulted
quantization_settings: QuantizationSettings = QuantizationSettings.load()
#: Instance of :class:`~scamp.settings.EngravingSettings` containing the actual engraving defaults to be consulted
engraving_settings: EngravingSettings = EngravingSettings.load()


def restore_all_factory_defaults(persist: bool = False) -> None:
    """
    Restores all settings back to their "factory defaults" (the defaults when SCAMP was installed).
    Unless the `persist` argument is set, this is temporary to the running of the current script.

    :param persist: if True, rewrites the JSON files from which defaults are loaded, meaning that this reset will
        persist to the running of scripts in the future.
    """
    playback_settings.restore_factory_defaults()
    if persist:
        playback_settings.make_persistent()

    quantization_settings.restore_factory_defaults()
    if persist:
        quantization_settings.make_persistent()

    engraving_settings.restore_factory_defaults()
    if persist:
        engraving_settings.make_persistent()
