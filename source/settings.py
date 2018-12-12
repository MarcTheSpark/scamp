from types import SimpleNamespace
from scamp.utilities import resolve_relative_path, SavesToJSON
from scamp.playback_adjustments import PlaybackDictionary, NotePlaybackAdjustment
from scamp.spelling import SpellingPolicy
import logging
import json


class ScampSettings(SimpleNamespace, SavesToJSON):

    _keys_to_leave_as_dicts = ()
    _factory_defaults = {}
    _settings_name = "Settings"
    _json_path = None

    def __init__(self, settings_dict, factory_defaults=None, keys_to_leave_as_dicts=None,
                 attribute_validation_function=None):
        factory_defaults = self._factory_defaults if factory_defaults is None else factory_defaults
        keys_to_leave_as_dicts = self._keys_to_leave_as_dicts \
            if keys_to_leave_as_dicts is None else keys_to_leave_as_dicts
        if attribute_validation_function is not None:
            self.validate_attribute = attribute_validation_function
        settings_arguments = {}
        for key in set(settings_dict.keys()).union(set(factory_defaults.keys())):
            if key in settings_dict and key in factory_defaults:
                # there is both an explicitly given setting and a factory default
                if isinstance(factory_defaults[key], SavesToJSON):
                    # if the factory default is a custom scamp class that serializes to or from json
                    # then we use that class's "from_json" method to load up the setting
                    settings_arguments[key] = type(factory_defaults[key]).from_json(settings_dict[key])
                elif isinstance(settings_dict[key], dict) and key not in keys_to_leave_as_dicts:
                    # otherwise, if this key points to a dictionary, and we haven't been told to leave it that way
                    # then we convert that dictionary to a ScampSettings namespace
                    settings_arguments[key] = ScampSettings(
                        settings_dict[key], factory_defaults[key], keys_to_leave_as_dicts,
                        attribute_validation_function=self.validate_attribute
                    )
                else:
                    # if neither of the above is true, then it's clearly just json-ready data
                    settings_arguments[key] = settings_dict[key]
            elif key in settings_dict:
                # there is no factory default for this key, which really shouldn't happen
                # it suggests someone added something to the json file that shouldn't be there
                logging.warning("Unexpected key \"{}\" in {}".format(
                    key, self._json_path if self._json_path is not None else "settings"
                ))
            else:
                # no setting given in the settings_dict, so we fall back to the factory default
                if isinstance(factory_defaults[key], dict) and not isinstance(factory_defaults[key], SavesToJSON) \
                        and key not in keys_to_leave_as_dicts:
                    # if it's a dict, but not a custom scamp class, and we've not been told to leave it as a dictionary
                    # then we convert the dictionary to a ScampSettings namespace
                    settings_arguments[key] = ScampSettings(
                        factory_defaults[key], factory_defaults[key], keys_to_leave_as_dicts=keys_to_leave_as_dicts,
                        attribute_validation_function=self.validate_attribute
                    )
                else:
                    # otherwise, we just take the default as is
                    settings_arguments[key] = factory_defaults[key]
            settings_arguments[key] = self.validate_attribute(key, settings_arguments[key])
        super().__init__(**settings_arguments)

    @staticmethod
    def nested_dict_from_nested_settings(nested_settings):
        if isinstance(nested_settings, ScampSettings):
            nested_settings = vars(nested_settings)
            if "validate_attribute" in nested_settings:
                # this is a little klugey, but the issue is that ScampSettings objects for sub-settings need to use
                # the validate_attribute method of their parent, so I explicitly set that method, but then it appears
                # in the __dict__ of the settings object and must be deleted manually before serializing to json
                del nested_settings["validate_attribute"]
        if hasattr(nested_settings, "to_json"):
            return nested_settings.to_json()
        elif isinstance(nested_settings, dict):
            return {key: ScampSettings.nested_dict_from_nested_settings(value)
                    for key, value in nested_settings.items()}
        else:
            return nested_settings

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
        json_dict = ScampSettings.nested_dict_from_nested_settings(self)
        return json_dict

    @classmethod
    def from_json(cls, json_object):
        return cls(json_object, cls._factory_defaults, cls._keys_to_leave_as_dicts)

    @classmethod
    def load(cls):
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

    def validate_attribute(self, key, value):
        return value

    def __setattr__(self, key, value):
        super().__setattr__(key, self.validate_attribute(key, value))


class PlaybackSettings(ScampSettings):

    _factory_defaults = {
        "default_soundfonts": {
            "default": "Merlin.sf2",
            "piano": "GrandPiano.sf2"
        },
        "default_audio_driver": "auto",
        "default_midi_output_device": None,
        "default_max_midi_pitch_bend": 48,
        "osc_message_addresses": {
            "start_note": "start_note",
            "end_note": "end_note",
            "change_pitch": "change_pitch",
            "change_volume": "change_volume",
            "change_quality": "change_quality"
        },
        "adjustments": PlaybackDictionary(articulations={
            "staccato": NotePlaybackAdjustment.scale_params(length_scale=0.5),
            "staccatissimo": NotePlaybackAdjustment.scale_params(length_scale=0.3),
            "tenuto": NotePlaybackAdjustment.scale_params(length_scale=1.2),
            "accent": NotePlaybackAdjustment.scale_params(volume_scale=1.2),
            "marcato": NotePlaybackAdjustment.scale_params(volume_scale=1.5),
        })
    }

    _keys_to_leave_as_dicts = ("default_soundfonts", "osc_message_addresses")
    _settings_name = "Playback settings"
    _json_path = "settings/playbackSettings.json"

    def __init__(self, settings_dict, factory_defaults=None, keys_to_leave_as_dicts=None):
        self.default_soundfonts = self.default_audio_driver = self.default_midi_output_device = \
            self.default_max_midi_pitch_bend = self.osc_message_addresses = self.adjustments = None
        super().__init__(settings_dict, factory_defaults, keys_to_leave_as_dicts)

    def register_default_soundfont(self, name: str, soundfont_path: str):
        """
        Adds a default named soundfont, so that it can be easily referred to in constructing a Session
        :param name: the default soundfont name
        :param soundfont_path: the absolute path to the soundfont, staring with a slash, or a relative path that
        gets resolved relative to the thirdparty/soundfonts directory
        """
        self.default_soundfonts[name] = soundfont_path

    def unregister_default_soundfont(self, name: str):
        """
        Same as above, but removes a default named soundfont
        :param name: the default soundfont name to remove
        """
        if name not in self.default_soundfonts:
            logging.warning("Tried to unregister default soundfont '{}', but it didn't exist.".format(name))
            return
        del self.default_soundfonts[name]

    def get_default_soundfonts(self):
        return self.default_soundfonts

    def list_default_soundfonts(self):
        for a, b in self.get_default_soundfonts().items():
            print("{}: {}".format(a, b))


class QuantizationSettings(ScampSettings):

    _factory_defaults = {
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


class EngravingSettings(ScampSettings):

    __slots__ = ("hello", )

    _factory_defaults = {
        "max_voices_per_part": 4,
        "max_dots_allowed": 3,
        "articulation_split_protocols": {  # can be first, last, or both
            "staccato": "last",
            "staccatissimo": "last",
            "marcato": "first",
            "tenuto": "last",
            "accent": "first"
        },
        "default_titles": ["On the Code Again", "The Long and Winding Code", "Code To Joy",
                           "Take Me Home, Country Codes", "Thunder Code", "Code to Nowhere",
                           "Goodbye Yellow Brick Code", "Hit the Code, Jack"],
        "default_composers": ["HTMLvis", "Rustin Beiber", "Javan Morrison", "Sia++",
                              "The Rubytles", "CSStiny's Child", "Perl Jam", "PHPrince", ],
        "default_spelling_policy": SpellingPolicy.from_string("C"),
        "ignore_empty_parts": True,
        "glissandi": {
            # control_point_policy can be either "grace", "split", or "none"
            # - if "grace", the rhythm is expressed as simply as possible and they are engraved as headless grace notes
            # - if "split", the note is split rhythmically at the control points
            # - if "none", control points are ignored
            "control_point_policy": "split",
            # if true, we consider all control points in the engraving process.
            # If false, we only consider local extrema.
            "consider_non_extrema_control_points": False,
            # if true, the final pitch reached is expressed as a gliss up to a headless grace note
            "include_end_grace_note": True,
            # this threshold helps determine which gliss control points are worth expressing in notation
            # the further a control point is from its neighbors, and the further it deviates from
            # the linearly interpolated pitch at that point, the higher its relevance score.
            "inner_grace_relevance_threshold": 4.0,
            "max_inner_graces_music_xml": 1
        },
        "tempo": {
            "include_guide_marks": False,
            "guide_mark_spacing": 0.5
        },
        "pad_incomplete_parts": True,
        "show_music_xml_command_line": "musescore",
    }

    _keys_to_leave_as_dicts = ("articulation_split_protocols", )
    _settings_name = "Engraving settings"
    _json_path = "settings/engravingSettings.json"

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

    def validate_attribute(self, key, value):
        if key == "max_voices_per_part" and not (isinstance(value, int) and 1 <= value <= 4):
            logging.warning("Invalid value \"{}\" for max_voices_per_part: must be an integer from 1 to 4. defaulting "
                            "to {}".format(value, EngravingSettings._factory_defaults["max_voices_per_part"]))
        elif key == "control_point_policy" and value not in ("grace", "split", "none"):
            logging.warning(
                "Invalid value of \"{}\" for glissando control point policy: must be one of: \"grace\", \"split\", or "
                "\"none\". Defaulting to \"{}\".".format(
                    value, EngravingSettings._factory_defaults["glissandi"]["control_point_policy"]
                )
            )
        elif key == "default_composers" and not isinstance(value, (list, str, type(None))):
            logging.warning("Default composers not understood: must be a list, string, or None. "
                            "Falling back to defaults.")
        elif key == "default_titles" and not isinstance(value, (list, str, type(None))):
            logging.warning("Default titles not understood: must be a list, string, or None. Falling back to defaults.")

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
