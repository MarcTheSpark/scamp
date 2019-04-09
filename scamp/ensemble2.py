from .soundfont_host import *
from .instruments2 import ScampInstrument
from .utilities import SavesToJSON
import logging


# TODO: FIX SAVING AND LOADING FROM JSON!!!


class Ensemble(SavesToJSON):

    def __init__(self, default_audio_driver="default", default_soundfont="default", default_midi_output_device=None):
        self.default_audio_driver = default_audio_driver
        self.default_soundfont = default_soundfont
        self.default_midi_output_device = default_midi_output_device

        self.instruments = []
        self.shared_resources = {}

    def add_instrument(self, instrument: ScampInstrument):
        """
        Adds an instance of ScampInstrument to this Ensemble. Generally this will be done indirectly
        by calling one of the "new_instrument" methods
        """
        assert isinstance(instrument, ScampInstrument)
        if not hasattr(instrument, "name") or instrument.name is None:
            instrument.name = "Track " + str(len(self.instruments) + 1)
        instrument.ensemble = self
        self.instruments.append(instrument)
        return instrument

    def new_silent_instrument(self, name=None):
        """
        Adds a silent instrument with no playback implementations
        """
        return self.add_instrument(ScampInstrument(name, self))

    def new_instrument(self, name=None, preset="auto", soundfont="default", num_channels=8,
                       audio_driver="default", max_pitch_bend="default"):
        """
        The default "new_instrument" is going to employ the SoundfontPlaybackImplementation, and by default,
        it will search for a preset that matches the name given.
        :param name: name used for this instrument in score, etc.
        :param preset: if an int, assumes bank #0; can also be a tuple of form (bank, preset). If "auto", searches
        for a preset of the appropriate name.
        :param soundfont: the name of the soundfont to use for fluidsynth playback
        :param num_channels: maximum of midi channels available to this midi part. It's wise to use more when doing
        microtonal playback, since pitch bends are applied per channel.
        :param audio_driver: which audio driver to use for this instrument (defaults to ensemble default)
        :param max_pitch_bend: max pitch bend to use for this instrument
        """
        audio_driver = self.default_audio_driver if audio_driver == "default" else audio_driver

        if preset == "auto":
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
        elif isinstance(preset, int):
            preset = (0, preset)

        name = "Track " + str(len(self.instruments) + 1) if name is None else name

        instrument = self.new_silent_instrument(name)
        instrument.add_soundfont_playback(preset, soundfont, num_channels, audio_driver, max_pitch_bend)

        return instrument

    # def add_silent_part(self, name=None):
    #     """
    #     Constructs a basic (and therefore silent) ScampInstrument, adds it to the Ensemble, and returns it
    #     :rtype : ScampInstrument
    #     """
    #     name = "Track " + str(len(self.instruments) + 1) if name is None else name
    #     instrument = ScampInstrument(self, name=name)
    #     self.add_part(instrument)
    #     return instrument
    #
    # def add_osc_part(self, port, name=None, ip_address="127.0.0.1", message_prefix=None,
    #                  osc_message_addresses="default"):
    #     """
    #     Constructs an OSCScampInstrument, adds it to the Ensemble, and returns it
    #     :param port: The port to send OSC Messages to (required)
    #     :param name: The name of the instrument
    #     :param ip_address: IP Address to send to; defaults to localhost
    #     :param message_prefix: the first part of the message address. Defaults to name or "unnamed" if name is None.
    #     If two instruments have the same name, this can be used to give them distinct messages
    #     :param osc_message_addresses: A dictionary defining the strings used in the address of different kinds of
    #     messages. The defaults are defined in playbackSettings.json, and you probably would never change them. But
    #     just in case you have no control over which messages you listen for, the option is there.
    #     :rtype : OSCScampInstrument
    #     """
    #     name = "Track " + str(len(self.instruments) + 1) if name is None else name
    #     instrument = OSCScampInstrument(self, name=name, port=port, ip_address=ip_address,
    #                                          message_prefix=message_prefix, osc_message_addresses=osc_message_addresses)
    #     self.add_part(instrument)
    #     return instrument

    def get_part_name_count(self, name):
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

    def to_json(self):
        return {
            "midi_player": self.midi_player.to_json(),
            "instruments": [
                instrument.to_json() for instrument in self.instruments
            ]
        }

    @classmethod
    def from_json(cls, json_dict, host_session=None):
        ensemble = cls(host_session)
        ensemble.midi_player = CombinedMidiPlayer.from_json(json_dict["midi_player"])
        for json_instrument in json_dict["instruments"]:
            ensemble.add_part(ScampInstrument.from_json(json_instrument, ensemble))
        return ensemble
