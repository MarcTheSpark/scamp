from .utilities import resolve_relative_path
import json


class SoundfontSettings:

    @staticmethod
    def restore_factory_defaults():
        SoundfontSettings._save_defaults_to_disk({
            "default": "Merlin.sf2",
            "piano": "GrandPiano.sf2"
        })

    @staticmethod
    def register_default_soundfont(name: str, soundfont_path: str):
        """
        Adds a default named soundfont, so that it can be easily referred to in constructing a Playcorder
        :param name: the default soundfont name
        :param soundfont_path: the absolute path to the soundfont, staring with a slash, or a relative path that
        gets resolved relative to the thirdparty/soundfonts directory
        """
        default_soundfonts = SoundfontSettings.get_default_soundfonts()
        default_soundfonts[name] = soundfont_path
        SoundfontSettings._save_defaults_to_disk(default_soundfonts)

    @staticmethod
    def unregister_default_soundfont(name: str):
        """
        Same as above, but removes a default named soundfont
        :param name: the default soundfont name to remove
        """
        default_soundfonts = SoundfontSettings.get_default_soundfonts()
        del default_soundfonts[name]
        SoundfontSettings._save_defaults_to_disk(default_soundfonts)

    @staticmethod
    def get_default_soundfonts():
        with open(resolve_relative_path("settings/soundfontSettings.json"), 'r') as soundfont_settings_file:
            default_soundfonts = json.load(soundfont_settings_file)
        return default_soundfonts

    @staticmethod
    def _save_defaults_to_disk(default_soundfonts):
        with open(resolve_relative_path("settings/soundfontSettings.json"), 'w') as soundfont_settings_file:
            json.dump(default_soundfonts, soundfont_settings_file, sort_keys=True, indent=4)


soundfont_settings = SoundfontSettings()


def restore_all_factory_defaults():
    soundfont_settings.restore_factory_defaults()
