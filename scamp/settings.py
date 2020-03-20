"""
Module containing the main settings classes: :class:`PlaybackSettings`, :class:`QuantizationSettings`, and
:class:`EngravingSettings`, as well as :class:`TempoSettings` and :class:`GlissandiSettings`, which are part of
:class:`EngravingSettings`. A module-level instance for each (:code:`playback_settings`, :code:`quantization_settings`,
and :code:`engraving_settings`) is loaded from JSON configuration files within within the settings directory of the
scamp package. These instances are part of the global scamp namespace, and contain scamp's default configuration.
"""
from types import SimpleNamespace
from .utilities import resolve_relative_path, SavesToJSON
from .playback_adjustments import PlaybackAdjustmentsDictionary, NotePlaybackAdjustment
from . import spelling
import logging
import json
import platform
import shutil
import subprocess
from typing import Optional


class _ScampSettings(SimpleNamespace, SavesToJSON):

    """Base class for scamp settings classes."""

    factory_defaults = {}
    _settings_name = "Settings"
    _json_path = None
    _is_root_setting = False

    def __init__(self, settings_dict: dict = None):
        if settings_dict is None:
            settings_arguments = self.factory_defaults
        else:
            settings_arguments = {}
            for key in set(settings_dict.keys()).union(set(self.factory_defaults.keys())):
                if key in settings_dict and key in self.factory_defaults:
                    # there is both an explicitly given setting and a factory default
                    if isinstance(self.factory_defaults[key], SavesToJSON):
                        # if the factory default is a custom scamp class that serializes to or from json (including
                        # another _ScampSettings derivative), then we use that class's "from_json" method to load it
                        settings_arguments[key] = type(self.factory_defaults[key])._from_json(settings_dict[key])
                    else:
                        # otherwise it should just be a simple json-friendly piece of data
                        settings_arguments[key] = settings_dict[key]
                elif key in settings_dict:
                    # there is no factory default for this key, which really shouldn't happen
                    # it suggests someone added something to the json file that shouldn't be there
                    logging.warning("Unexpected key \"{}\" in {}".format(
                        key, self._json_path if self._json_path is not None else "settings"
                    ))
                else:
                    # no setting given in the settings_dict, so we fall back to the factory default
                    settings_arguments[key] = self.factory_defaults[key]
                settings_arguments[key] = self._validate_attribute(key, settings_arguments[key])
        super().__init__(**settings_arguments)

    def restore_factory_defaults(self, persist=False) -> None:
        """
        Restores settings back to their "factory defaults" (the defaults when SCAMP was installed).
        Unless the `persist` argument is set, this is temporary to the running of the current script.

        :param persist: if True, rewrites the JSON file from which defaults are loaded, meaning that this reset will
            persist to the running of scripts in the future.
        """
        for key in self._factory_defaults:
            vars(self)[key] = self._factory_defaults[key]
        if persist:
            self.make_persistent()

    def make_persistent(self) -> None:
        """
        Rewrites the JSON file from which settings are loaded, meaning that this reset will persist to the running of
        scripts in the future.
        """
        self.save_to_json(resolve_relative_path(self._json_path))

    @classmethod
    def factory_default(cls):
        """
        Returns a factory default version of this settings object.
        """
        return cls({})

    def _to_json(self):
        return {key: value._to_json() if hasattr(value, "_to_json") else value for key, value in vars(self).items()}

    @classmethod
    def _from_json(cls, json_object):
        return cls(json_object)

    @classmethod
    def load(cls):
        """
        Loads and instance of this settings object from its corresponding JSON file. If no such file exists, or it is
        corrupted in some way, then this creates a fresh JSON file there. This doesn't work with settings that are
        nested within other settings (like GlissandiSettings), since they do not have corresponding JSON files,
        """
        assert cls._is_root_setting, "Cannot load a non-root setting automatically."
        try:
            return cls.load_from_json(resolve_relative_path(cls._json_path))
        except FileNotFoundError:
            logging.warning("{} not found; generating defaults.".format(cls._settings_name))
            factory_defaults = cls.factory_default()
            factory_defaults.make_persistent()
            return factory_defaults
        except (TypeError, json.decoder.JSONDecodeError):
            logging.warning("Error loading {}; falling back to defaults.".format(cls._settings_name.lower()))
            return cls.factory_default()

    @staticmethod
    def _validate_attribute(key, value):
        return value

    def __setattr__(self, key, value):
        if all(x is None for x in vars(self).values()):
            # this avoids validation warnings getting sent out when we set the instance variables of subclasses
            # to None at the beginning of their __init__ calls (which we do as a hint to IDEs)
            super().__setattr__(key, value)
        else:
            super().__setattr__(key, self._validate_attribute(key, value))


class PlaybackSettings(_ScampSettings):

    """
    Namespace containing the settings relevant to playback implementation and adjustments.

    :param settings_dict: dictionary from which to set all settings attributes
    :ivar named_soundfonts: Dictionary mapping names of frequently-used soundfonts to their file paths
    :ivar default_soundfont: Soundfont (by name or path) to default to in playback
    :ivar default_audio_driver: Name of the audio driver use for soundfont playback by default. If "auto", we test to
        see what audio driver will work, and replace this value with that driver.
    :ivar default_midi_output_device: Name or number of the midi output device to default to
    :ivar default_max_soundfont_pitch_bend: When playing back with soundfonts, instruments will be immediately set
        to use this value for the maximum pitch bend. (Makes sense to set this to a large value for maximum flexibility)
    :ivar default_max_streaming_midi_pitch_bend: When playing back with a midi stream to an external
        synthesizer/program, instruments will be immediately set to use this value for the maximum pitch bend. (Makes
        sense probably to leave this at the MIDI default of 2 semitones, in case the receiving device doesn't listen
        to messages that reset the pitch bend range.)
    :ivar osc_message_addresses: Dictionary mapping the different kinds of playback messages to the OSC messages
        prefixes we will use for them. For instance, if you want start note messages to use "note_on", set the
        osc_message_addresses["start_note"] = "note_on", and all OSC messages starting a note will come out as
        [instrument name]/note_on/
    :ivar adjustments: a :class:`scamp.playback_adjustments.PlaybackAdjustmentsDictionary` defining how playback should
        be altered in response to different articulations/notations/etc.
    :ivar try_system_fluidsynth_first: if True, always tries system copy of the fluidsynth libraries first before using
        the one embedded in the scamp package.
    """

    #: Default playback settings (from when SCAMP was installed)
    factory_defaults = {
        "named_soundfonts": {
            "general_midi": "Merlin.sf2",
        },
        "default_soundfont": "general_midi",
        "default_audio_driver": "auto",
        "default_midi_output_device": None,
        "default_max_soundfont_pitch_bend": 48,
        "default_max_streaming_midi_pitch_bend": 2,
        "osc_message_addresses": {
            "start_note": "start_note",
            "end_note": "end_note",
            "change_pitch": "change_pitch",
            "change_volume": "change_volume",
            "change_parameter": "change_parameter"
        },
        "adjustments": PlaybackAdjustmentsDictionary(articulations={
            "staccato": NotePlaybackAdjustment.scale_params(length=0.5),
            "staccatissimo": NotePlaybackAdjustment.scale_params(length=0.3),
            "tenuto": NotePlaybackAdjustment.scale_params(length=1.2),
            "accent": NotePlaybackAdjustment.scale_params(volume=1.2),
            "marcato": NotePlaybackAdjustment.scale_params(volume=1.5),
        }),
        "try_system_fluidsynth_first": False,
    }

    _settings_name = "Playback settings"
    _json_path = "settings/playbackSettings.json"
    _is_root_setting = True

    def __init__(self, settings_dict: dict = None):
        # This is here to help with auto-completion so that the IDE knows what attributes are available
        self.named_soundfonts = self.default_soundfont = self.default_audio_driver = \
            self.default_midi_output_device = self.default_max_soundfont_pitch_bend = \
            self.default_max_streaming_midi_pitch_bend = self.osc_message_addresses = \
            self.adjustments = self.try_system_fluidsynth_first = None
        super().__init__(settings_dict)
        assert isinstance(self.adjustments, PlaybackAdjustmentsDictionary)

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
        :class:`scamp.quantization.BeatQuantizationScheme`)
    :ivar simplicity_preference: float representing the default degree of preference for simple beat divisors. (See
        :class:`scamp.quantization.BeatQuantizationScheme`)
    :ivar default_time_signature: string (e.g. "4/4") representing the default time signature to use when one is not
        specified.
    """

    #: Default quantization settings (from when SCAMP was installed)
    factory_defaults = {
        "onset_weighting": 1.0,
        "termination_weighting": 0.5,
        "inner_split_weighting": 0.75,
        "max_divisor": 8,
        "max_divisor_indigestibility": None,
        "simplicity_preference": 2.0,
        "default_time_signature": "4/4"
    }

    _settings_name = "Quantization settings"
    _json_path = "settings/quantizationSettings.json"
    _is_root_setting = True

    def __init__(self, settings_dict: dict = None):
        # This is here to help with auto-completion so that the IDE knows what attributes are available
        self.onset_weighting = self.termination_weighting = self.inner_split_weighting = self.max_divisor = \
            self.max_divisor_indigestibility = self.simplicity_preference = self.default_time_signature = None
        super().__init__(settings_dict)


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

    #: Default glissandi-related settings (from when SCAMP was installed)
    factory_defaults = {
        "control_point_policy": "split",
        "consider_non_extrema_control_points": True,
        "include_end_grace_note": True,
        "inner_grace_relevance_threshold": 1.5,
        "max_inner_graces_music_xml": 1
    }

    _settings_name = "Glissandi settings"
    _json_path = "settings/engravingSettings.json"
    _is_root_setting = False

    def __init__(self, settings_dict: dict = None):
        # This is here to help with auto-completion so that the IDE knows what attributes are available
        self.control_point_policy = self.consider_non_extrema_control_points = self.include_end_grace_note = \
            self.inner_grace_relevance_threshold = self.max_inner_graces_music_xml = None
        super().__init__(settings_dict)

    @staticmethod
    def _validate_attribute(key, value):
        if key == "control_point_policy" and value not in ("grace", "split", "none"):
            logging.warning(
                "Invalid value of \"{}\" for glissando control point policy: must be one of: \"grace\", \"split\", or "
                "\"none\". Defaulting to \"{}\".".format(
                    value, GlissandiSettings.factory_defaults["control_point_policy"]
                )
            )
            return GlissandiSettings.factory_defaults["control_point_policy"]
        return value


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

    #: Default tempo-related settings (from when SCAMP was installed)
    factory_defaults = {
        "guide_mark_resolution": 0.125,
        "guide_mark_sensitivity": 0.08,
        "include_guide_marks": True,
        "parenthesize_guide_marks": True
    }

    _settings_name = "Tempo settings"
    _json_path = "settings/engravingSettings.json"
    _is_root_setting = False

    def __init__(self, settings_dict: dict = None):
        self.guide_mark_resolution = self.guide_mark_sensitivity = self.include_guide_marks = \
            self.parenthesize_guide_marks = None
        super().__init__(settings_dict)


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
    :ivar show_music_xml_command_line: Terminal command to run when opening up MusicXML scores. It is easiest to set
        this by calling set_music_xml_application. The value "auto" tries to find an appropriate application
        automatically.
    :ivar show_microtonal_annotations: if True, annotates microtonal pitches with the exact floating-point MIDI pitch
        value that they are intended to represent. (This is useful, since normally the best a notation program can
        do is quarter tones.
    """

    #: Default engraving settings (from when SCAMP was installed)
    factory_defaults = {
        "allow_duple_tuplets_in_compound_time": True,
        "max_voices_per_part": 4,
        "max_dots_allowed": 3,
        "beat_hierarchy_spacing": 2.4,
        "num_divisions_penalty": 0.6,
        "rest_beat_hierarchy_spacing": 20,
        "rest_num_divisions_penalty": 0.2,
        "articulation_split_protocols": {
            "staccato": "last",
            "staccatissimo": "last",
            "marcato": "first",
            "tenuto": "both",
            "accent": "first"
        },
        "clefs_by_instrument": {
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
            "DEFAULT": ["treble", "bass"]
        },
        "clef_pitch_centers": {
            "bass": 50,
            "tenor": 57,
            "alto": 60,
            "treble": 71,
            "soprano": 67,
            "mezzo-soprano": 64,
            "baritone": 53,
        },
        "clef_selection_policy": "measure-wise",
        "default_titles": ["On the Code Again", "The Long and Winding Code", "Code To Joy",
                           "Take Me Home, Country Codes", "Thunder Code", "Code to Nowhere",
                           "Goodbye Yellow Brick Code", "Hit the Code, Jack"],
        "default_composers": ["HTMLvis", "Rustin Beiber", "Javan Morrison", "Sia++",
                              "The Rubytles", "CSStiny's Child", "Perl Jam", "PHPrince", ],
        "default_spelling_policy": spelling.SpellingPolicy.from_string("C"),
        "ignore_empty_parts": True,
        "glissandi": GlissandiSettings(),
        "tempo": TempoSettings(),
        "pad_incomplete_parts": True,
        "show_music_xml_command_line": "auto",
        "show_microtonal_annotations": False,
    }

    _settings_name = "Engraving settings"
    _json_path = "settings/engravingSettings.json"
    _is_root_setting = True

    def __init__(self, settings_dict: dict = None):
        # This is here to help with auto-completion so that the IDE knows what attributes are available
        self.max_voices_per_part = self.max_dots_allowed = self.beat_hierarchy_spacing = self.num_divisions_penalty = \
            self.rest_beat_hierarchy_spacing = self.rest_num_divisions_penalty = self.articulation_split_protocols = \
            self.default_titles = self.default_composers = self.default_spelling_policy = self.ignore_empty_parts = \
            self.pad_incomplete_parts = self.show_music_xml_command_line = self.show_microtonal_annotations = \
            self.allow_duple_tuplets_in_compound_time = self.clefs_by_instrument = self.clef_pitch_centers = \
            self.clef_selection_policy = None
        self.glissandi: GlissandiSettings = None
        self.tempo: TempoSettings = None
        super().__init__(settings_dict)
        if self.show_music_xml_command_line is None or self.show_music_xml_command_line == "auto":
            self._auto_set_music_xml_open_command()
            self.make_persistent()

    def _auto_set_music_xml_open_command(self):
        print("Testing for software to open MusicXML files...")
        app_names_to_try = ["MuseScore", "Sibelius", "Finale", "Dorico"]
        platform_system = platform.system().lower()
        if platform_system == "linux":
            for cmd in [x.lower() for x in app_names_to_try] + app_names_to_try:
                if shutil.which(cmd) is not None:
                    print("Found application {}. This has been made the default, but it can be altered by running "
                          "engraving_settings.set_music_xml_application(NAME_OF_APPLICATION)".format(cmd))
                    self.set_music_xml_application(cmd)
                    return
            # if we can't find the appropriate application, set it to a generic open command
            print("Could not find an appropriate application; falling back to generic open command.")
            self.set_music_xml_application()
        elif platform_system == "windows":
            program_list = subprocess.check_output(["cmd", "/c", "wmic", "product", "get", "name"]).decode().\
                replace(" ", "").split("\r\r\n")
            for app_name in app_names_to_try:
                for installed_program in program_list:
                    if app_name.lower() in installed_program.lower():
                        print("Found application {}. This has been made the default, but it can be altered by running "
                              "engraving_settings.set_music_xml_application(NAME_OF_APPLICATION)".
                              format(installed_program))
                        self.set_music_xml_application(installed_program)
                        return
            print("Could not find an appropriate application; falling back to generic open command.")
            self.set_music_xml_application()
        elif platform_system == "darwin":
            for app_name in app_names_to_try:
                if subprocess.call(["open", "-Ra", app_name]) == 0:
                    print("Found application {}. This has been made the default, but it can be altered by running "
                          "engraving_settings.set_music_xml_application(NAME_OF_APPLICATION)".format(app_name))
                    self.set_music_xml_application(app_name)
                    return
            # if we can't find the appropriate application, set it to a generic open command
            print("Could not find an appropriate application; falling back to generic open command.")
            self.set_music_xml_application()
        else:
            logging.warning("Unrecognized platform {}".format(platform_system))

    def set_music_xml_application(self, application_name: str = None) -> None:
        """
        Sets the application to use when opening generated MusicXML scores

        :param application_name: name of the application to use. If None, defaults to a generic file open command.
        """
        platform_system = platform.system().lower()
        if platform_system == "linux":
            # generic open command on linux is "xdg-open"
            self.show_music_xml_command_line = application_name if application_name is not None else "xdg-open"
        elif platform_system == "darwin":
            # generic open command on mac is "open"
            self.show_music_xml_command_line = "open -a {}".format(application_name) \
                if application_name is not None else "open"
        elif platform_system == "windows":
            # generic open command on windows is "start"
            self.show_music_xml_command_line = "cmd.exe /c start {}".format(application_name) \
                if application_name is not None else "start"
        else:
            logging.warning("Cannot run \"show_xml\" on unrecognized platform {}".format(platform_system))

    def get_default_title(self) -> Optional[str]:
        """Grabs one of the default score titles."""
        if isinstance(self.default_titles, list):
            import random
            return random.choice(self.default_titles)
        elif isinstance(self.default_titles, str):
            return self.default_titles
        else:
            return None

    def get_default_composer(self) -> Optional[str]:
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
            logging.warning("Invalid value \"{}\" for max_voices_per_part: must be an integer from 1 to 4. defaulting "
                            "to {}".format(value, EngravingSettings.factory_defaults["max_voices_per_part"]))
            return EngravingSettings.factory_defaults["max_voices_per_part"]
        elif key == "default_composers" and not isinstance(value, (list, str, type(None))):
            logging.warning("Default composers not understood: must be a list, string, or None. "
                            "Falling back to defaults.")
            return EngravingSettings.factory_defaults["default_composers"]
        elif key == "default_titles" and not isinstance(value, (list, str, type(None))):
            logging.warning("Default titles not understood: must be a list, string, or None. Falling back to defaults.")
            return EngravingSettings.factory_defaults["default_titles"]
        elif key == "clef_selection_policy" and value not in ["measure-wise", "part-wise"]:
            logging.warning("Clef selection policy must be either \"measure-wise\" or \"part-wise\"."
                            "Falling back to defaults.")
            return EngravingSettings.factory_defaults["clef_selection_policy"]
        return value


#: Instance of PlaybackSettings containing the actual playback defaults that are consulted
playback_settings: PlaybackSettings = PlaybackSettings.load()
#: Instance of QuantizationSettings containing the actual quantization defaults that are consulted
quantization_settings: QuantizationSettings = QuantizationSettings.load()
#: Instance of EngravingSettings containing the actual engraving defaults that are consulted
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
