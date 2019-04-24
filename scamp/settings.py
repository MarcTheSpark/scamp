from types import SimpleNamespace
from .utilities import resolve_relative_path, SavesToJSON
from .playback_adjustments import PlaybackDictionary, NotePlaybackAdjustment
from .spelling import SpellingPolicy
import logging
import json


class ScampSettings(SimpleNamespace, SavesToJSON):

    factory_defaults = {}
    _settings_name = "Settings"
    _json_path = None
    _is_root_setting = False

    def __init__(self, settings_dict=None):
        if settings_dict is None:
            settings_arguments = self.factory_defaults
        else:
            settings_arguments = {}
            for key in set(settings_dict.keys()).union(set(self.factory_defaults.keys())):
                if key in settings_dict and key in self.factory_defaults:
                    # there is both an explicitly given setting and a factory default
                    if isinstance(self.factory_defaults[key], SavesToJSON):
                        # if the factory default is a custom scamp class that serializes to or from json (including
                        # another ScampSettings derivative), then we use that class's "from_json" method to load it
                        settings_arguments[key] = type(self.factory_defaults[key]).from_json(settings_dict[key])
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

    def restore_factory_defaults(self):
        for key in self._factory_defaults:
            vars(self)[key] = self._factory_defaults[key]
        return self

    def make_persistent(self):
        self.save_to_json(resolve_relative_path(self._json_path))

    @classmethod
    def factory_default(cls):
        return cls({})

    def to_json(self):
        return {key: value.to_json() if hasattr(value, "to_json") else value for key, value in vars(self).items()}

    @classmethod
    def from_json(cls, json_object):
        return cls(json_object)

    @classmethod
    def load(cls):
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


class PlaybackSettings(ScampSettings):

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
        "adjustments": PlaybackDictionary(articulations={
            "staccato": NotePlaybackAdjustment.scale_params(length=0.5),
            "staccatissimo": NotePlaybackAdjustment.scale_params(length=0.3),
            "tenuto": NotePlaybackAdjustment.scale_params(length=1.2),
            "accent": NotePlaybackAdjustment.scale_params(volume=1.2),
            "marcato": NotePlaybackAdjustment.scale_params(volume=1.5),
        })
    }

    _settings_name = "Playback settings"
    _json_path = "settings/playbackSettings.json"
    _is_root_setting = True

    def __init__(self, settings_dict=None):
        # This is here to help with auto-completion so that the IDE knows what attributes are available
        self.named_soundfonts = self.default_soundfont = self.default_audio_driver = \
            self.default_midi_output_device = self.default_max_soundfont_pitch_bend = \
            self.default_max_streaming_midi_pitch_bend = self.osc_message_addresses = \
            self.adjustments = None
        super().__init__(settings_dict)
        assert isinstance(self.adjustments, PlaybackDictionary)

    def register_named_soundfont(self, name: str, soundfont_path: str):
        """
        Adds a named soundfont, so that it can be easily referred to in constructing a Session
        :param name: the soundfont name
        :param soundfont_path: the absolute path to the soundfont, staring with a slash, or a relative path that
        gets resolved relative to the soundfonts directory
        """
        self.named_soundfonts[name] = soundfont_path

    def unregister_named_soundfont(self, name: str):
        """
        Same as above, but removes a named soundfont
        :param name: the default soundfont name to remove
        """
        if name not in self.named_soundfonts:
            logging.warning("Tried to unregister default soundfont '{}', but it didn't exist.".format(name))
            return
        del self.named_soundfonts[name]

    def list_named_soundfonts(self):
        for a, b in self.named_soundfonts.items():
            print("{}: {}".format(a, b))


class QuantizationSettings(ScampSettings):

    factory_defaults = {
        "onset_weighting": 1.0,
        "termination_weighting": 0.5,
        "inner_split_weighting": 0.75,
        "max_divisor": 8,
        "max_indigestibility": None,
        "simplicity_preference": 2.0,
        "default_time_signature": "4/4"
    }

    _settings_name = "Quantization settings"
    _json_path = "settings/quantizationSettings.json"
    _is_root_setting = True

    def __init__(self, settings_dict=None):
        # This is here to help with auto-completion so that the IDE knows what attributes are available
        self.onset_weighting = self.termination_weighting = self.inner_split_weighting = self.max_divisor = \
            self.max_indigestibility = self.simplicity_preference = self.default_time_signature = None
        super().__init__(settings_dict)


class GlissandiSettings(ScampSettings):

    factory_defaults = {
        # control_point_policy can be either "grace", "split", or "none"
        # - if "grace", the rhythm is expressed as simply as possible and they are engraved as headless grace notes
        # - if "split", the note is split rhythmically at the control points
        # - if "none", control points are ignored
        "control_point_policy": "split",
        # if true, we consider all control points in the engraving process.
        # If false, we only consider local extrema.
        "consider_non_extrema_control_points": True,
        # if true, the final pitch reached is expressed as a gliss up to a headless grace note
        "include_end_grace_note": True,
        # this threshold helps determine which gliss control points are worth expressing in notation
        # the further a control point is from its neighbors, and the further it deviates from
        # the linearly interpolated pitch at that point, the higher its relevance score.
        "inner_grace_relevance_threshold": 1.5,
        "max_inner_graces_music_xml": 1
    }

    _settings_name = "Glissandi settings"
    _json_path = "settings/engravingSettings.json"
    _is_root_setting = False

    def __init__(self, settings_dict=None):
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


class TempoSettings(ScampSettings):
    factory_defaults = {
        # grid that the guide marks are snapped to, in beats. Actual appearance of a guide mark depends on sensitivity.
        "guide_mark_resolution": 0.125,
        # guide_mark_sensitivity represents how much a tempo has to change proportionally to put a guide mark
        # so for instance, if it's 0.1 and the last notated tempo was 60, we'll put a guide mark when the
        # tempo reaches 60 +/- 0.1 * 60 = 54 or 66
        "guide_mark_sensitivity": 0.08,
        "include_guide_marks": True,
        "parenthesize_guide_marks": True
    }

    _settings_name = "Tempo settings"
    _json_path = "settings/engravingSettings.json"
    _is_root_setting = False

    def __init__(self, settings_dict=None):
        self.guide_mark_resolution = self.guide_mark_resolution = self.include_guide_marks = \
            self.parenthesize_guide_marks = None
        super().__init__(settings_dict)


class EngravingSettings(ScampSettings):

    factory_defaults = {
        "max_voices_per_part": 4,
        "max_dots_allowed": 3,
        "articulation_split_protocols": {
            # can be "first", "last", "both", or "all"
            # first means the articulation only appears at the beginning of a tied group
            # last means it only appears at the end
            # both means it appears at the beginning and the end
            # and all means that it even appears on inner tied notes
            "staccato": "last",
            "staccatissimo": "last",
            "marcato": "first",
            "tenuto": "both",
            "accent": "first"
        },
        "default_titles": ["On the Code Again", "The Long and Winding Code", "Code To Joy",
                           "Take Me Home, Country Codes", "Thunder Code", "Code to Nowhere",
                           "Goodbye Yellow Brick Code", "Hit the Code, Jack"],
        "default_composers": ["HTMLvis", "Rustin Beiber", "Javan Morrison", "Sia++",
                              "The Rubytles", "CSStiny's Child", "Perl Jam", "PHPrince", ],
        "default_spelling_policy": SpellingPolicy.from_string("C"),
        "ignore_empty_parts": True,
        "glissandi": GlissandiSettings(),
        "tempo": TempoSettings(),
        "pad_incomplete_parts": True,
        "show_music_xml_command_line": "musescore",
    }

    _settings_name = "Engraving settings"
    _json_path = "settings/engravingSettings.json"
    _is_root_setting = True

    def __init__(self, settings_dict=None):
        # This is here to help with auto-completion so that the IDE knows what attributes are available
        self.max_voices_per_part = self.max_dots_allowed = self.articulation_split_protocols = self.default_titles = \
            self.default_composers = self.default_spelling_policy = self.ignore_empty_parts = \
            self.pad_incomplete_parts = self.show_music_xml_command_line = None
        self.glissandi: GlissandiSettings = None
        self.tempo: TempoSettings = None
        super().__init__(settings_dict)

    def get_default_title(self):
        if isinstance(self.default_titles, list):
            import random
            return random.choice(self.default_titles)
        elif isinstance(self.default_titles, str):
            return self.default_titles
        else:
            return None

    def get_default_composer(self):
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
        return value


playback_settings = PlaybackSettings.load()
quantization_settings = QuantizationSettings.load()
engraving_settings = EngravingSettings.load()


def restore_all_factory_defaults(persist=False):
    playback_settings.restore_factory_defaults()
    if persist:
        playback_settings.make_persistent()

    quantization_settings.restore_factory_defaults()
    if persist:
        quantization_settings.make_persistent()

    engraving_settings.restore_factory_defaults()
    if persist:
        engraving_settings.make_persistent()
