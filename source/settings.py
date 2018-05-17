from playcorder.utilities import resolve_relative_path, SavesToJSON
import logging


class PlaybackSettings(SavesToJSON):

    def __init__(self, settings_dict):
        self.settings_dict = settings_dict

    def restore_factory_defaults(self):
        self.settings_dict = {
            "default soundfonts": {
                "default": "Merlin.sf2",
                "piano": "GrandPiano.sf2"
            },
            "audio_driver": None,
            "default_midi_output_device": None,
        }
        return self

    def register_default_soundfont(self, name: str, soundfont_path: str):
        """
        Adds a default named soundfont, so that it can be easily referred to in constructing a Playcorder
        :param name: the default soundfont name
        :param soundfont_path: the absolute path to the soundfont, staring with a slash, or a relative path that
        gets resolved relative to the thirdparty/soundfonts directory
        """
        self.settings_dict["default soundfonts"][name] = soundfont_path

    def unregister_default_soundfont(self, name: str):
        """
        Same as above, but removes a default named soundfont
        :param name: the default soundfont name to remove
        """
        if name not in self.settings_dict["default soundfonts"]:
            logging.warning("Tried to unregister default soundfont '{}', but it didn't exist.".format(name))
            return
        del self.settings_dict["default soundfonts"][name]

    def get_default_soundfonts(self):
        return self.settings_dict["default soundfonts"]

    def make_persistent(self):
        self.save_to_json(resolve_relative_path("settings/playbackSettings.json"))

    @property
    def default_audio_driver(self):
        return self.settings_dict["audio_driver"]

    @default_audio_driver.setter
    def default_audio_driver(self, audio_driver):
        self.settings_dict["audio_driver"] = audio_driver

    @property
    def default_midi_output_device(self):
        return self.settings_dict["default_midi_output_device"]

    @default_midi_output_device.setter
    def default_midi_output_device(self, default_midi_output_device):
        self.settings_dict["default_midi_output_device"] = default_midi_output_device

    @classmethod
    def factory_default(cls):
        return cls({}).restore_factory_defaults()

    def _to_json(self):
        return self.settings_dict

    @classmethod
    def _from_json(cls, json_object):
        return cls(json_object)


def restore_all_factory_defaults():
    PlaybackSettings({}).restore_factory_defaults().make_persistent()


try:
    playback_settings = PlaybackSettings.load_from_json(resolve_relative_path("settings/playbackSettings.json"))
except FileNotFoundError:
    playback_settings = PlaybackSettings.factory_default()
    playback_settings.make_persistent()
