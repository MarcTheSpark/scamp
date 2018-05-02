from .instruments import PlaycorderInstrument, MidiPlaycorderInstrument
from .combined_midi_player import CombinedMidiPlayer
from .utilities import SavesToJSON


class Ensemble(SavesToJSON):

    def __init__(self, soundfonts=None, audio_driver=None, default_midi_output_device=None):
        # if we are using just one soundfont a string is okay; we'll just put it in a list
        soundfonts = [soundfonts] if isinstance(soundfonts, str) else soundfonts

        self.midi_player = CombinedMidiPlayer(soundfonts, audio_driver, default_midi_output_device)
        self.instruments = []
        self.host_playcorder = None

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

    def add_part(self, instrument):
        """
        Adds an instance of PlaycorderInstrument to this Ensemble. Generally this will be done indirectly
        by calling add_midi_part, but this functionality is here so that people can build and use their own
        PlaycorderInstruments that implement the interface and playback sounds in different ways.
        :type instrument: PlaycorderInstrument
        """
        assert isinstance(instrument, PlaycorderInstrument)
        if not hasattr(instrument, "name") or instrument.name is None:
            instrument.name = "Track " + str(len(self.instruments) + 1)
        instrument.host_ensemble = self
        self.instruments.append(instrument)
        return instrument

    def add_midi_part(self, name=None, preset=(0, 0), soundfont_index=0, num_channels=8,
                      midi_output_device=None, midi_output_name=None):
        """
        Constructs a MidiPlaycorderInstrument, adds it to the Ensemble, and returns it
        :param name: name used for this instrument in score output and midi output (unless otherwise specified)
        :type name: str
        :param preset: if an int, assumes bank #0; can also be a tuple of form (bank, preset)
        :param soundfont_index: the index of the soundfont to use for fluidsynth playback
        :type soundfont_index: int
        :param num_channels: maximum of midi channels available to this midi part. It's wise to use more when doing
        microtonal playback, since pitch bends are applied per channel.
        :type num_channels: int
        :param midi_output_device: the name of the device to use for outgoing midi stream. Defaults to whatever was
        set as this playcorder's default
        :param midi_output_name: the name to use when outputting midi streams. Defaults to the name of the instrument.
        :rtype : MidiPlaycorderInstrument
        """

        if name is None:
            name = "Track " + str(len(self.instruments) + 1)

        if not 0 <= soundfont_index < len(self.midi_player.soundfont_ids):
            raise ValueError("Soundfont index out of bounds.")

        if isinstance(preset, int):
            preset = (0, preset)

        instrument = MidiPlaycorderInstrument(self, name, preset, soundfont_index, num_channels,
                                              midi_output_device, midi_output_name)

        self.add_part(instrument)
        return instrument

    def add_silent_part(self, name=None):
        """
        Constructs a basic (and therefore silent) PlaycorderInstrument, adds it to the Ensemble, and returns it
        :rtype : PlaycorderInstrument
        """
        name = "Track " + str(len(self.instruments) + 1) if name is None else name
        instrument = PlaycorderInstrument(self, name=name)
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

    def _to_json(self):
        return {
            "midi_player": self.midi_player._to_json(),
            "instruments": [
                instrument._to_json() for instrument in self.instruments
            ]
        }

    @classmethod
    def _from_json(cls, json_dict, host_playcorder=None):
        ensemble = cls(host_playcorder)
        ensemble.midi_player = CombinedMidiPlayer._from_json(json_dict["midi_player"])
        for json_instrument in json_dict["instruments"]:
            ensemble.add_part(PlaycorderInstrument._from_json(json_instrument, ensemble))
        return ensemble
