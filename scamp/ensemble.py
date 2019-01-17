from .instruments import ScampInstrument, MidiScampInstrument, OSCScampInstrument
from .combined_midi_player import CombinedMidiPlayer
from .utilities import SavesToJSON
import logging


# TODO: allow a silent MIDI Instrument to be created (e.g. "add_silent_midi_part") that outputs a MIDI stream only

class Ensemble(SavesToJSON):

    def __init__(self, soundfonts=None, audio_driver=None, default_midi_output_device=None):
        # if we are using just one soundfont a string is okay; we'll just put it in a list
        soundfonts = [soundfonts] if isinstance(soundfonts, str) else soundfonts

        # We always construct a CombinedMidiPlayer, but if no soundfonts are given, it's mostly a placeholder
        # FluidSynth only starts up when a soundfont is loaded. Similarly, the rtmidi output only functions ig
        # a midi_output_device is provided either to the CombinedMidiPlayer or the specific instrument
        self.midi_player = CombinedMidiPlayer(soundfonts, audio_driver, default_midi_output_device)
        self.instruments = []
        self.host_session = None

    @property
    def audio_driver(self):
        return self.midi_player.audio_driver

    @audio_driver.setter
    def audio_driver(self, driver):
        self.midi_player.audio_driver = driver

    def load_soundfont(self, soundfont):
        self.midi_player.load_soundfont(soundfont)

    @property
    def default_midi_output_device(self):
        return self.midi_player.rtmidi_output_device

    @default_midi_output_device.setter
    def default_midi_output_device(self, device):
        self.midi_player.rtmidi_output_device = device

    def get_instruments_with_substring(self, word, avoid=None, soundfont_index=0):
        return self.midi_player.get_instruments_with_substring(word, avoid=avoid, soundfont_index=soundfont_index)

    def iter_presets(self):
        return self.midi_player.iter_presets()

    def print_all_soundfont_presets(self):
        self.midi_player.print_all_soundfont_presets()

    def add_part(self, instrument):
        """
        Adds an instance of ScampInstrument to this Ensemble. Generally this will be done indirectly
        by calling add_midi_part, but this functionality is here so that people can build and use their own
        ScampInstruments that implement the interface and playback sounds in different ways.
        :type instrument: ScampInstrument
        """
        assert isinstance(instrument, ScampInstrument)
        if not hasattr(instrument, "name") or instrument.name is None:
            instrument.name = "Track " + str(len(self.instruments) + 1)
        instrument.host_ensemble = self
        self.instruments.append(instrument)
        return instrument

    def add_midi_part(self, name=None, preset="auto", soundfont_index=0, num_channels=8,
                      midi_output_device=None, midi_output_name=None):
        """
        Constructs a MidiScampInstrument, adds it to the Ensemble, and returns it
        :param name: name used for this instrument in score output and midi output (unless otherwise specified)
        :type name: str
        :param preset: if an int, assumes bank #0; can also be a tuple of form (bank, preset). If "auto", searches
        for a preset of the appropriate name.
        :param soundfont_index: the index of the soundfont to use for fluidsynth playback
        :type soundfont_index: int
        :param num_channels: maximum of midi channels available to this midi part. It's wise to use more when doing
        microtonal playback, since pitch bends are applied per channel.
        :type num_channels: int
        :param midi_output_device: the name of the device to use for outgoing midi stream. Defaults to whatever was
        set as this ensemble's default
        :param midi_output_name: the name to use when outputting midi streams. Defaults to the name of the instrument.
        :rtype : MidiScampInstrument
        """

        name = "Track " + str(len(self.instruments) + 1) if name is None else name

        if not 0 <= soundfont_index < len(self.midi_player.soundfont_ids):
            raise ValueError("Soundfont index out of bounds.")

        if preset == "auto":
            if name is None:
                preset = (0, 0)
            else:
                # strip any numbers and spaces from the name, so that "Clarinet 1" searches as "clarinet"
                possible_instruments = self.get_instruments_with_substring(name.strip(" 0123456789"))
                if len(possible_instruments) > 0:
                    preset = (possible_instruments[0].bank, possible_instruments[0].preset)
                else:
                    logging.warning("Could not find preset matching {}. "
                                    "Falling back to preset 0 (probably piano).".format(name))
                    preset = (0, 0)
        elif isinstance(preset, int):
            preset = (0, preset)

        instrument = MidiScampInstrument(self, name, preset, soundfont_index, num_channels,
                                         midi_output_device, midi_output_name)

        self.add_part(instrument)
        return instrument

    def add_silent_part(self, name=None):
        """
        Constructs a basic (and therefore silent) ScampInstrument, adds it to the Ensemble, and returns it
        :rtype : ScampInstrument
        """
        name = "Track " + str(len(self.instruments) + 1) if name is None else name
        instrument = ScampInstrument(self, name=name)
        self.add_part(instrument)
        return instrument

    def add_osc_part(self, port, name=None, ip_address="127.0.0.1", message_prefix=None,
                     osc_message_addresses="default"):
        """
        Constructs an OSCScampInstrument, adds it to the Ensemble, and returns it
        :param port: The port to send OSC Messages to (required)
        :param name: The name of the instrument
        :param ip_address: IP Address to send to; defaults to localhost
        :param message_prefix: the first part of the message address. Defaults to name or "unnamed" if name is None.
        If two instruments have the same name, this can be used to give them distinct messages
        :param osc_message_addresses: A dictionary defining the strings used in the address of different kinds of
        messages. The defaults are defined in playbackSettings.json, and you probably would never change them. But
        just in case you have no control over which messages you listen for, the option is there.
        :rtype : OSCScampInstrument
        """
        name = "Track " + str(len(self.instruments) + 1) if name is None else name
        instrument = OSCScampInstrument(self, name=name, port=port, ip_address=ip_address,
                                             message_prefix=message_prefix, osc_message_addresses=osc_message_addresses)
        self.add_part(instrument)
        return instrument

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
