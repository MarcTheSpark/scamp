from .soundfont_host import *
from .instruments import ScampInstrument
from .spelling import SpellingPolicy
from .utilities import SavesToJSON
import logging


class Ensemble(SavesToJSON):

    """
    Host for multiple ScampInstruments, keeping shared resources, and shared default settings.
    A Session is, among other things, an Ensemble.

    :param default_audio_driver: value to initialize default_audio_driver instance variable to
    :param default_soundfont: value to initialize default_soundfont instance variable to
    :param default_midi_output_device: value to initialize default_midi_output_device instance variable to
    :ivar default_audio_driver: the audio driver instruments in this ensemble will default to. If "default", then
        this defers to the scamp global playback_settings default.
    :ivar default_soundfont: the soundfont that instruments in this ensemble will default to. If "default", then
        this defers to the scamp global playback_settings default.
    :ivar default_midi_output_device: the midi output device that instruments in this ensemble will default to.
        If "default", then this defers to the scamp global playback_settings default.
    :ivar instruments: List of all of the ScampInstruments within the Ensemble.
    :type instruments: list
    """

    def __init__(self, default_soundfont="default", default_audio_driver="default",
                 default_midi_output_device="default"):

        self.default_soundfont = default_soundfont
        self.default_audio_driver = default_audio_driver
        self.default_midi_output_device = default_midi_output_device

        self._default_spelling_policy = None

        self.instruments = []
        self.shared_resources = {}

    def add_instrument(self, instrument: ScampInstrument):
        """
        Adds an instance of ScampInstrument to this Ensemble. Generally this will be done indirectly
        by calling one of the "new_instrument" methods.
        """
        assert isinstance(instrument, ScampInstrument)
        if not hasattr(instrument, "name") or instrument.name is None:
            instrument.name = "Track " + str(len(self.instruments) + 1)
        instrument.ensemble = self
        self.instruments.append(instrument)
        return instrument

    def new_silent_part(self, name=None):
        """
        Creates and returns a new ScampInstrument for this Ensemble with no PlaybackImplementations.

        :param name: name of the new part
        :return: the newly created ScampInstrument
        """
        return self.add_instrument(ScampInstrument(name, self))

    @staticmethod
    def _resolve_preset_from_name(name, soundfont):
        # if preset is auto, try to find a match in the soundfont
        if name is None:
            preset = (0, 0)
        else:
            preset_match, match_score = get_best_preset_match_for_name(name, which_soundfont=soundfont)
            if match_score > 1.0:
                preset = preset_match.bank, preset_match.preset
                print("Using preset {} for {}".format(preset_match.name, name))
            else:
                logging.warning("Could not find preset matching {}. "
                                "Falling back to preset 0 (probably piano).".format(name))
                preset = (0, 0)
        return preset

    def new_part(self, name=None, preset="auto", soundfont="default", num_channels=8,
                 audio_driver="default", max_pitch_bend="default"):
        """
        Creates and returns a new ScampInstrument for this Ensemble that uses a SoundfontPlaybackImplementation. Unless
        otherwise specified, the default soundfont for this Ensemble/Session will be used, and we will search for the
        preset that best matches the name given.

        :param name: name used for this instrument in score, etc.
        :param preset: if an int, assumes bank #0; can also be a tuple of form (bank, preset). If "auto", searches
            for a preset of the appropriate name.
        :param soundfont: the name of the soundfont to use for fluidsynth playback
        :param num_channels: maximum of midi channels available to this midi part. It's wise to use more when doing
            microtonal playback, since pitch bends are applied per channel.
        :param audio_driver: which audio driver to use for this instrument (defaults to ensemble default)
        :param max_pitch_bend: max pitch bend to use for this instrument
        :return: the newly created ScampInstrument
        """
        # Resolve soundfont and audio driver to ensemble defaults if necessary (these may well be the string
        # "default", in which case it gets resolved to the playback_settings default)
        soundfont = self.default_soundfont if soundfont == "default" else soundfont
        audio_driver = self.default_audio_driver if audio_driver == "default" else audio_driver

        # if preset is auto, try to find a match in the soundfont
        if preset == "auto":
            preset = Ensemble._resolve_preset_from_name(name, soundfont)
        elif isinstance(preset, int):
            preset = (0, preset)

        name = "Track " + str(len(self.instruments) + 1) if name is None else name

        instrument = self.new_silent_part(name)
        instrument.add_soundfont_playback(preset, soundfont, num_channels, audio_driver, max_pitch_bend)

        return instrument

    def new_midi_part(self, name=None, midi_output_device="default", num_channels=8,
                      midi_output_name=None, max_pitch_bend="default"):
        """
        Creates and returns a new ScampInstrument for this Ensemble that uses a MIDIStreamPlaybackImplementation.
        This means that when notes are played by this instrument, midi messages are sent out to the given device.

        :param name: name used for this instrument in score, etc. for a preset of the appropriate name.
        :param midi_output_device: name or number of the device used to output midi. Call
            get_available_ports_and_devices to check what's available.
        :param num_channels: maximum of midi channels available to this midi part. It's wise to use more when doing
            microtonal playback, since pitch bends are applied per channel.
        :param midi_output_name: name of this part
        :param max_pitch_bend: max pitch bend to use for this instrument
        :return: the newly created ScampInstrument
        """
        midi_output_device = self.default_midi_output_device if midi_output_device == "default" else midi_output_device

        name = "Track " + str(len(self.instruments) + 1) if name is None else name

        instrument = self.new_silent_part(name)
        instrument.add_streaming_midi_playback(midi_output_device, num_channels, midi_output_name, max_pitch_bend)

        return instrument

    def new_osc_part(self, name=None, port=None, ip_address="127.0.0.1", message_prefix=None,
                     osc_message_addresses="default"):
        """
        Creates and returns a new ScampInstrument for this Ensemble that uses a OSCPlaybackImplementation. This means
        that when notes are played by this instrument, osc messages are sent out to the specified address

        :param name: name used for this instrument in score, etc. for a preset of the appropriate name.
        :param port: port osc messages are sent to
        :param ip_address: ip_address osc messages are sent to
        :param message_prefix: prefix used for this instrument in osc messages
        :param osc_message_addresses: dictionary defining the address used for each type of playback message. defaults
            to using "start_note", "end_note", "change_pitch", "change_volume", "change_parameter". The default can
            be changed in playback settings.
        :return: the newly created ScampInstrument
        """
        name = "Track " + str(len(self.instruments) + 1) if name is None else name

        instrument = self.new_silent_part(name)
        instrument.add_osc_playback(port, ip_address, message_prefix, osc_message_addresses)

        return instrument

    def _get_part_name_count(self, name):
        return sum(i.name == name for i in self.instruments)

    def get_instrument_by_name(self, name, which=0):
        """
        Returns the instrument of the given name. If there are multiple with the same name, the which parameter
        specifies the one returned. (If none match the number given by which, the first name match is returned)
        """
        # if there are multiple instruments of the same name, which determines which one is chosen
        imperfect_match = None
        for instrument in self.instruments:
            if name == instrument.name:
                if which == instrument.name_count:
                    return instrument
                else:
                    imperfect_match = instrument if imperfect_match is None else imperfect_match
        return imperfect_match

    def print_default_soundfont_presets(self):
        """
        Prints a list of presets available with the default soundfont.
        """
        print_soundfont_presets(self.default_soundfont)

    @property
    def default_spelling_policy(self):
        """
        Default spelling policy used for transcriptions made with this Ensemble.
        """
        return self._default_spelling_policy

    @default_spelling_policy.setter
    def default_spelling_policy(self, value):
        if value is None or isinstance(value, SpellingPolicy):
            self._default_spelling_policy = value
        elif isinstance(value, str):
            self._default_spelling_policy = SpellingPolicy.from_string(value)
        else:
            raise ValueError("Spelling policy not understood.")

    def _to_json(self):
        return {
            "default_soundfont": self.default_soundfont,
            "default_audio_driver": self.default_audio_driver,
            "default_midi_output_device": self.default_midi_output_device,
            "default_spelling_policy": self.default_spelling_policy,
            "instruments": [instrument._to_json() for instrument in self.instruments]
        }

    @classmethod
    def _from_json(cls, json_dict):
        json_instruments = json_dict.pop("instruments")
        default_spelling_policy = json_dict.pop("default_spelling_policy")
        ensemble = cls(**json_dict)
        ensemble.default_spelling_policy = default_spelling_policy
        ensemble.instruments = [ScampInstrument._from_json(json_instrument, ensemble)
                                for json_instrument in json_instruments]
        return ensemble

    def __repr__(self):
        return "Ensemble.from_json({})".format(self._to_json())
