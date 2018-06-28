from playcorder.utilities import resolve_relative_path, SavesToJSON
import logging


_playback_settings_factory_defaults = {
    "default_soundfonts": {
        "default": "Merlin.sf2",
        "piano": "GrandPiano.sf2"
    },
    "default_audio_driver": None,
    "default_midi_output_device": None,
}


class PlaybackSettings(SavesToJSON):

    def __init__(self, **settings):
        self.default_soundfonts = None if "default_soundfonts" not in settings else settings["default_soundfonts"]
        self.default_audio_driver = None if "default_audio_driver" not in settings else settings["default_audio_driver"]
        self.default_midi_output_device = None if "default_midi_output_device" not in settings \
            else settings["default_midi_output_device"]

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
        return self.__dict__

    @classmethod
    def _from_json(cls, json_object):
        return cls(**json_object)


_quantization_settings_factory_defaults = {
    "onset_weighting": 1.0,
    "termination_weighting": 0.5,
    "max_divisor": 8,
    "max_indigestibility": None,
    "simplicity_preference": 2.0
}


class QuantizationSettings(SavesToJSON):

    def __init__(self, **settings):
        self.onset_weighting = None if "onset_weighting" not in settings else settings["onset_weighting"]
        self.termination_weighting = None if "termination_weighting" not in settings \
            else settings["termination_weighting"]
        self.max_divisor = None if "max_divisor" not in settings else settings["max_divisor"]
        self.max_indigestibility = None if "max_indigestibility" not in settings else settings["max_indigestibility"]
        self.simplicity_preference = None if "simplicity_preference" not in settings \
            else settings["simplicity_preference"]

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
}


class EngravingSettings(SavesToJSON):

    def __init__(self, **settings):
        self.max_voices_per_part = None if "max_voices_per_part" not in settings else settings["max_voices_per_part"]

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
    playback_settings = PlaybackSettings.factory_default()
    playback_settings.make_persistent()


try:
    quantization_settings = \
        QuantizationSettings.load_from_json(resolve_relative_path("settings/quantizationSettings.json"))
except FileNotFoundError:
    quantization_settings = QuantizationSettings.factory_default()
    quantization_settings.make_persistent()


try:
    engraving_settings = EngravingSettings.load_from_json(resolve_relative_path("settings/engravingSettings.json"))
except FileNotFoundError:
    engraving_settings = EngravingSettings.factory_default()
    engraving_settings.make_persistent()


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
