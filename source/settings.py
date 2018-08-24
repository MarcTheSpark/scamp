from playcorder.utilities import resolve_relative_path, SavesToJSON
from playcorder.playback_adjustments import PlaybackDictionary, NotePlaybackAdjustment
import json
import logging


_playback_settings_factory_defaults = {
    "default_soundfonts": {
        "default": "Merlin.sf2",
        "piano": "GrandPiano.sf2"
    },
    "default_audio_driver": None,
    "default_midi_output_device": None,
    "osc_message_defaults": {
        "start_note_message_string": "start_note",
        "end_note_message_string": "end_note",
        "change_pitch_message_string": "change_pitch",
        "change_volume_message_string": "change_volume",
        "change_quality_message_string": "change_quality"
    },
    "adjustments": PlaybackDictionary(articulations={
        "staccato": NotePlaybackAdjustment.scale_params(length_scale=0.5)
    })
}


class PlaybackSettings(SavesToJSON):

    def __init__(self, **settings):
        self.default_soundfonts = _playback_settings_factory_defaults["default_soundfonts"] \
            if "default_soundfonts" not in settings else settings["default_soundfonts"]
        self.default_audio_driver = _playback_settings_factory_defaults["default_audio_driver"] \
            if "default_audio_driver" not in settings else settings["default_audio_driver"]
        self.default_midi_output_device = _playback_settings_factory_defaults["default_midi_output_device"] \
            if "default_midi_output_device" not in settings else settings["default_midi_output_device"]
        self.osc_message_defaults = _playback_settings_factory_defaults["osc_message_defaults"] \
            if "osc_message_defaults" not in settings else settings["osc_message_defaults"]
        self.adjustments = _playback_settings_factory_defaults["adjustments"] \
            if "adjustments" not in settings else settings["adjustments"]

    def restore_factory_defaults(self):
        for key in _playback_settings_factory_defaults:
            self.__dict__[key] = _playback_settings_factory_defaults[key]
        return self

    def register_default_soundfont(self, name: str, soundfont_path: str):
        """
        Adds a default named soundfont, so that it can be easily referred to in constructing a Playcorder
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

    def make_persistent(self):
        self.save_to_json(resolve_relative_path("settings/playbackSettings.json"))

    @classmethod
    def factory_default(cls):
        return cls().restore_factory_defaults()

    def _to_json(self):
        return {key: value._to_json() if hasattr(value, "_to_json") else value for key, value in self.__dict__.items()}

    @classmethod
    def _from_json(cls, json_object):
        if "adjustments" in json_object:
            json_object["adjustments"] = PlaybackDictionary._from_json(json_object["adjustments"])
        return cls(**json_object)


_quantization_settings_factory_defaults = {
    "onset_weighting": 1.0,
    "termination_weighting": 0.5,
    "max_divisor": 8,
    "max_indigestibility": None,
    "simplicity_preference": 2.0,
    "default_time_signature": "4/4"
}


class QuantizationSettings(SavesToJSON):

    def __init__(self, **settings):
        self.onset_weighting = _quantization_settings_factory_defaults["onset_weighting"] \
            if "onset_weighting" not in settings else settings["onset_weighting"]
        self.termination_weighting = _quantization_settings_factory_defaults["termination_weighting"] \
            if "termination_weighting" not in settings else settings["termination_weighting"]
        self.max_divisor = _quantization_settings_factory_defaults["max_divisor"] \
            if "max_divisor" not in settings else settings["max_divisor"]
        self.max_indigestibility = _quantization_settings_factory_defaults["max_indigestibility"] \
            if "max_indigestibility" not in settings else settings["max_indigestibility"]
        self.simplicity_preference = _quantization_settings_factory_defaults["simplicity_preference"] \
            if "simplicity_preference" not in settings else settings["simplicity_preference"]
        self.default_time_signature = _quantization_settings_factory_defaults["default_time_signature"] \
            if "default_time_signature" not in settings else settings["default_time_signature"]

    def restore_factory_defaults(self):
        for key in _quantization_settings_factory_defaults:
            self.__dict__[key] = _quantization_settings_factory_defaults[key]
        return self

    def make_persistent(self):
        self.save_to_json(resolve_relative_path("settings/quantizationSettings.json"))

    @classmethod
    def factory_default(cls):
        return cls().restore_factory_defaults()

    def _to_json(self):
        return self.__dict__

    @classmethod
    def _from_json(cls, json_object):
        return cls(**json_object)


_engraving_settings_factory_defaults = {
    "max_voices_per_part": 4,
    "max_dots_allowed": 3,
    "default_titles": ["Digging Deep", "I Like Fruit", "My Soup is Too Cold", "Woe is Me", "Dope Soundscapes",
                       "Black and White Life", "Pistol-Whipped Gyrations In A Petri Dish", "Carry on, Carrion",
                       "Color Me Blue", "Atomic Cucumbers", "If My Cat Could Smoke"],
    "default_composers": ["Gold-E-Lox", "50 Cent", "Eric Whitacre", "J. Bieber", "Honey Boo Boo", "Rebecca Black"]
}


class EngravingSettings(SavesToJSON):

    def __init__(self, **settings):
        self._max_voices_per_part = _engraving_settings_factory_defaults["max_voices_per_part"] \
            if "max_voices_per_part" not in settings else settings["max_voices_per_part"]
        assert isinstance(self._max_voices_per_part, int) and 0 <= self._max_voices_per_part < 5, \
            "Max voices per part must be an integer from 1 to 4"
        self.max_dots_allowed = _engraving_settings_factory_defaults["max_dots_allowed"] \
            if "max_dots_allowed" not in settings else settings["max_dots_allowed"]
        self.default_titles = _engraving_settings_factory_defaults["default_titles"] \
            if "default_titles" not in settings else settings["default_titles"]
        self.default_composers = _engraving_settings_factory_defaults["default_composers"] \
            if "default_composers" not in settings else settings["default_composers"]

    @property
    def max_voices_per_part(self):
        return self._max_voices_per_part

    @max_voices_per_part.setter
    def max_voices_per_part(self, value):
        assert isinstance(value, int) and 0 <= value < 5, "Max voices per part must be an integer from 1 to 4"
        self._max_voices_per_part = value

    def restore_factory_defaults(self):
        for key in _engraving_settings_factory_defaults:
            self.__dict__[key] = _engraving_settings_factory_defaults[key]
        return self

    def make_persistent(self):
        self.save_to_json(resolve_relative_path("settings/engravingSettings.json"))

    @classmethod
    def factory_default(cls):
        return cls().restore_factory_defaults()

    def _to_json(self):
        return self.__dict__

    @classmethod
    def _from_json(cls, json_object):
        return cls(**json_object)


try:
    playback_settings = PlaybackSettings.load_from_json(resolve_relative_path("settings/playbackSettings.json"))
except FileNotFoundError:
    logging.warning("Playback settings not found; generating defaults.")
    playback_settings = PlaybackSettings.factory_default()
    playback_settings.make_persistent()
except (TypeError, json.decoder.JSONDecodeError):
    logging.warning("Error loading playback settings; falling back to defaults.")
    playback_settings = PlaybackSettings.factory_default()


try:
    quantization_settings = \
        QuantizationSettings.load_from_json(resolve_relative_path("settings/quantizationSettings.json"))
except FileNotFoundError:
    logging.warning("Quantization settings not found; generating defaults.")
    quantization_settings = QuantizationSettings.factory_default()
    quantization_settings.make_persistent()
except (TypeError, json.decoder.JSONDecodeError):
    logging.warning("Error loading quantization settings; falling back to defaults.")
    quantization_settings = QuantizationSettings.factory_default()

try:
    engraving_settings = EngravingSettings.load_from_json(resolve_relative_path("settings/engravingSettings.json"))
except (FileNotFoundError, json.decoder.JSONDecodeError):
    logging.warning("Engraving settings not found; generating defaults.")
    engraving_settings = EngravingSettings.factory_default()
    engraving_settings.make_persistent()
except (TypeError, json.decoder.JSONDecodeError):
    logging.warning("Error loading engraving settings; falling back to defaults.")
    engraving_settings = EngravingSettings.factory_default()


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
