from scamp.utilities import resolve_relative_path, SavesToJSON
from scamp.playback_adjustments import PlaybackDictionary, NotePlaybackAdjustment
from scamp.spelling import SpellingPolicy
import json
import logging

_playback_settings_factory_defaults = {
    "default_soundfonts": {
        "default": "Merlin.sf2",
        "piano": "GrandPiano.sf2"
    },
    "default_audio_driver": None,
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


class PlaybackSettings(SavesToJSON):

    def __init__(self, **settings):
        self.default_soundfonts = _playback_settings_factory_defaults["default_soundfonts"] \
            if "default_soundfonts" not in settings else settings["default_soundfonts"]
        self.default_audio_driver = _playback_settings_factory_defaults["default_audio_driver"] \
            if "default_audio_driver" not in settings else settings["default_audio_driver"]
        self.default_midi_output_device = _playback_settings_factory_defaults["default_midi_output_device"] \
            if "default_midi_output_device" not in settings else settings["default_midi_output_device"]
        self.default_max_midi_pitch_bend = _playback_settings_factory_defaults["default_max_midi_pitch_bend"] \
            if "default_max_midi_pitch_bend" not in settings else settings["default_max_midi_pitch_bend"]
        self.osc_message_addresses = _playback_settings_factory_defaults["osc_message_addresses"] \
            if "osc_message_addresses" not in settings else settings["osc_message_addresses"]
        self.adjustments = _playback_settings_factory_defaults["adjustments"] \
            if "adjustments" not in settings else settings["adjustments"]

    def restore_factory_defaults(self):
        for key in _playback_settings_factory_defaults:
            self.__dict__[key] = _playback_settings_factory_defaults[key]
        return self

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

    def make_persistent(self):
        self.save_to_json(resolve_relative_path("settings/playbackSettings.json"))

    def to_json(self):
        return {key: value.to_json() if hasattr(value, "to_json") else value for key, value in self.__dict__.items()}

    @classmethod
    def from_json(cls, json_object):
        if "adjustments" in json_object:
            json_object["adjustments"] = PlaybackDictionary.from_json(json_object["adjustments"])
        return cls(**json_object)


_quantization_settings_factory_defaults = {
    "onset_weighting": 1.0,
    "termination_weighting": 0.5,
    "inner_split_weighting": 0.75,
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
        self.inner_split_weighting = _quantization_settings_factory_defaults["inner_split_weighting"] \
            if "inner_split_weighting" not in settings else settings["inner_split_weighting"]
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
        return cls()

    def to_json(self):
        return self.__dict__

    @classmethod
    def from_json(cls, json_object):
        return cls(**json_object)


_glissandi_engraving_factory_defaults = {
    # control_point_policy can be either "grace", "split", or "none"
    # - if "grace", the rhythm is expressed as simply as possible and they are engraved as headless grace notes
    # - if "split", the note is split rhythmically at the control points
    # - if "none", control points are ignored
    "control_point_policy": "split",
    # if true, we consider all control points in the engraving process. If false, we only consider local extrema.
    "consider_non_extrema_control_points": False,
    # if true, the final pitch reached is expressed as a gliss up to a headless grace note
    "include_end_grace_note": True,
    # this threshold helps determine which gliss control points are worth expressing in notation
    # the further a control point is from its neighbors, and the further it deviates from
    # the linearly interpolated pitch at that point, the higher its relevance score.
    "inner_grace_relevance_threshold": 4.0,
    "max_inner_graces_music_xml": 1
}


class GlissandiEngravingSettings(SavesToJSON):

    def __init__(self, **settings):
        self._control_point_policy = _glissandi_engraving_factory_defaults["control_point_policy"] \
            if "control_point_policy" not in settings else settings["control_point_policy"]
        try:
            assert self.control_point_policy in ("grace", "split", "none")
        except AssertionError:
            logging.warning("Control point policy must be one of: \"grace\", \"split\", or \"none\". Defaulting "
                            "to \"{}\".".format(_glissandi_engraving_factory_defaults["control_point_policy"]))
            self.control_point_policy = _glissandi_engraving_factory_defaults["control_point_policy"]
        self.consider_non_extrema_control_points = \
            _glissandi_engraving_factory_defaults["consider_non_extrema_control_points"] \
            if "consider_non_extrema_control_points" not in settings \
                else settings["consider_non_extrema_control_points"]
        self.include_end_grace_note = _glissandi_engraving_factory_defaults["include_end_grace_note"] \
            if "include_end_grace_note" not in settings else settings["include_end_grace_note"]
        self.inner_grace_relevance_threshold = _glissandi_engraving_factory_defaults["inner_grace_relevance_threshold"] \
            if "inner_grace_relevance_threshold" not in settings else settings["inner_grace_relevance_threshold"]
        self.max_inner_graces_music_xml = _glissandi_engraving_factory_defaults["max_inner_graces_music_xml"] \
            if "max_inner_graces_music_xml" not in settings else settings["max_inner_graces_music_xml"]

    @property
    def control_point_policy(self):
        return self._control_point_policy

    @control_point_policy.setter
    def control_point_policy(self, value):
        assert value in ("grace", "split", "none"), \
            "Control point policy must be one of: \"grace\", \"split\", or \"none\""
        self._control_point_policy = value

    def to_json(self):
        return {key.strip("_"): value for key, value in self.__dict__.items()}

    @classmethod
    def from_json(cls, json_object):
        return cls(**json_object)


_engraving_settings_factory_defaults = {
    "max_voices_per_part": 4,
    "max_dots_allowed": 3,
    "articulation_split_protocols": {  # can be first, last, or both
        "staccato": "last",
        "staccatissimo": "last",
        "marcato": "first",
        "tenuto": "last",
        "accent": "first"
    },
    "default_titles": ["On the Code Again", "The Long and Winding Code", "Code To Joy", "Take Me Home, Country Codes",
                       "Thunder Code", "Code to Nowhere", "Goodbye Yellow Brick Code", "Hit the Code, Jack"],
    "default_composers": ["HTMLvis", "Rustin Beiber", "Javan Morrison", "Sia++", "The Rubytles", "CSStiny's Child",
                          "Perl Jam", "PHPrince", ],
    "default_spelling_policy": SpellingPolicy.from_string("c major"),
    "ignore_empty_parts": True,
    "glissandi": GlissandiEngravingSettings(),
    "pad_incomplete_parts": True,
    "show_music_xml_command_line": "musescore",
}


class EngravingSettings(SavesToJSON):

    def __init__(self, **settings):
        self._max_voices_per_part = _engraving_settings_factory_defaults["max_voices_per_part"] \
            if "max_voices_per_part" not in settings else settings["max_voices_per_part"]
        assert isinstance(self._max_voices_per_part, int) and 0 <= self._max_voices_per_part < 5, \
            "Max voices per part must be an integer from 1 to 4"
        self.max_dots_allowed = _engraving_settings_factory_defaults["max_dots_allowed"] \
            if "max_dots_allowed" not in settings else settings["max_dots_allowed"]
        self.articulation_split_protocols = _engraving_settings_factory_defaults["articulation_split_protocols"] \
            if "articulation_split_protocols" not in settings else settings["articulation_split_protocols"]
        self.default_titles = _engraving_settings_factory_defaults["default_titles"] \
            if "default_titles" not in settings else settings["default_titles"]
        assert isinstance(self.default_titles, (list, str, type(None))), "Default titles not understood."
        self.default_composers = _engraving_settings_factory_defaults["default_composers"] \
            if "default_composers" not in settings else settings["default_composers"]
        assert isinstance(self.default_composers, (list, str, type(None))), "Default composers not understood."
        self.default_spelling_policy = _engraving_settings_factory_defaults["default_spelling_policy"] \
            if "default_spelling_policy" not in settings \
            else SpellingPolicy.from_string(settings["default_spelling_policy"]) \
            if isinstance(settings["default_spelling_policy"], str) else settings["default_spelling_policy"]
        self.glissandi = GlissandiEngravingSettings(**_glissandi_engraving_factory_defaults) \
            if "glissandi" not in settings else GlissandiEngravingSettings(**settings["glissandi"]) \
            if isinstance(settings["glissandi"], dict) else settings["glissandi"]
        self.ignore_empty_parts = _engraving_settings_factory_defaults["ignore_empty_parts"] \
            if "ignore_empty_parts" not in settings else settings["ignore_empty_parts"]
        self.pad_incomplete_parts = _engraving_settings_factory_defaults["pad_incomplete_parts"] \
            if "pad_incomplete_parts" not in settings else settings["pad_incomplete_parts"]
        self.show_music_xml_command_line = _engraving_settings_factory_defaults["show_music_xml_command_line"] \
            if "show_music_xml_command_line" not in settings else settings["show_music_xml_command_line"]

    @property
    def max_voices_per_part(self):
        return self._max_voices_per_part

    @max_voices_per_part.setter
    def max_voices_per_part(self, value):
        assert isinstance(value, int) and 0 <= value < 5, "Max voices per part must be an integer from 1 to 4"
        self._max_voices_per_part = value

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

    def restore_factory_defaults(self):
        for key in _engraving_settings_factory_defaults:
            self.__dict__[key] = _engraving_settings_factory_defaults[key]
        return self

    def make_persistent(self):
        self.save_to_json(resolve_relative_path("settings/engravingSettings.json"))

    def to_json(self):
        return {x.strip("_"): (self.__dict__[x].to_json() if hasattr(self.__dict__[x], "to_json")
                               else self.__dict__[x]) for x in self.__dict__}

    @classmethod
    def from_json(cls, json_object):
        return cls(**json_object)


try:
    playback_settings = PlaybackSettings.load_from_json(resolve_relative_path("settings/playbackSettings.json"))
except FileNotFoundError:
    logging.warning("Playback settings not found; generating defaults.")
    playback_settings = PlaybackSettings()
    playback_settings.make_persistent()
except (TypeError, json.decoder.JSONDecodeError):
    logging.warning("Error loading playback settings; falling back to defaults.")
    playback_settings = PlaybackSettings()


try:
    quantization_settings = \
        QuantizationSettings.load_from_json(resolve_relative_path("settings/quantizationSettings.json"))
except FileNotFoundError:
    logging.warning("Quantization settings not found; generating defaults.")
    quantization_settings = QuantizationSettings()
    quantization_settings.make_persistent()
except (TypeError, json.decoder.JSONDecodeError):
    logging.warning("Error loading quantization settings; falling back to defaults.")
    quantization_settings = QuantizationSettings()


try:
    engraving_settings = EngravingSettings.load_from_json(resolve_relative_path("settings/engravingSettings.json"))
except FileNotFoundError:
    logging.warning("Engraving settings not found; generating defaults.")
    engraving_settings = EngravingSettings()
    engraving_settings.make_persistent()
except (TypeError, json.decoder.JSONDecodeError):
    logging.warning("Error loading engraving settings; falling back to defaults.")
    engraving_settings = EngravingSettings()


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
