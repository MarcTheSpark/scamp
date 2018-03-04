from .playcorder_utilities import resolve_relative_path
from .simple_rtmidi_wrapper import SimpleRtMidiOut
from collections import OrderedDict

fluidsynth_loaded = False
try:
    from .thirdparty.fluidsynth import Synth
    fluidsynth_loaded = True
except ImportError:
    Synth = None
    print("Fluidsynth could not be loaded; synth output will not be available.")

sf2utils_loaded = False
try:
    from sf2utils.sf2parse import Sf2File
    sf2utils_loaded = True
except ImportError:
    Sf2File = None
    print("sf2utils was not found; info about soundfont presets will not be available.")


# load up all of the default soundfonts and their paths
with open(resolve_relative_path('thirdparty/soundfonts/defaultSoundfonts.txt'), 'r') as f:
    _defaultSoundfonts = OrderedDict()
    for line in f.read().split("\n"):
        name_and_path = line.split(', ')
        if len(name_and_path) >= 2:
            _defaultSoundfonts[name_and_path[0]] = name_and_path[1]


def register_default_soundfont(name, soundfont_path):
    """
    Adds a default named soundfont, so that it can be easily referred to in constructing a Playcorder
    :param name: the name to refer to the soundfont as
    :type name: str
    :param soundfont_path: the absolute path to the soundfont, staring with a slash, or a relative path that
    gets resolved relative to the thirdparty/soundfonts directory
    :type soundfont_path: str
    """
    _defaultSoundfonts[name] = soundfont_path
    with open(resolve_relative_path('thirdparty/soundfonts/defaultSoundfonts.txt'), 'w') as defaults_file:
        defaults_file.writelines([', '.join(x) + '\n' for x in _defaultSoundfonts.items()])


def unregister_default_soundfont(name):
    """
    Same as above, but removes a default named soundfont
    :param name: the default soundfont name to remove
    :type name: str
    """
    del _defaultSoundfonts[name]

    with open(resolve_relative_path('thirdparty/soundfonts/defaultSoundfonts.txt'), 'w') as defaults_file:
        defaults_file.writelines([', '.join(x) + '\n' for x in _defaultSoundfonts.items()])


class CombinedMidiPlayer:

    def __init__(self, soundfonts=None, driver=None, rtmidi_output_device=None):

        self.used_channels = 0  # how many channels have we already assigned to various instruments

        self.synth = None
        self.soundfont_ids = []  # the ids of loaded soundfonts
        self.soundfont_instrument_lists = []

        if soundfonts is not None and fluidsynth_loaded:
            soundfont_paths = []
            for soundfont in soundfonts:
                if soundfont in _defaultSoundfonts:
                    soundfont_path = _defaultSoundfonts[soundfont]
                    if soundfont_path.startswith("./"):
                        soundfont_path = resolve_relative_path("thirdparty/soundfonts/" + soundfont_path[2:])
                    elif not soundfont_path.startswith("/"):
                        soundfont_path = resolve_relative_path("thirdparty/soundfonts/" + soundfont_path)
                    soundfont_paths.append(soundfont_path)
                else:
                    soundfont_paths.append(soundfont)

                if sf2utils_loaded:
                    # if we have sf2utils, load up the preset info from the soundfonts
                    with open(soundfont_paths[-1], "rb") as sf2_file:
                        sf2 = Sf2File(sf2_file)
                        self.soundfont_instrument_lists.append(sf2.presets)

            self.initialize_fluidsynth(soundfont_paths, driver=driver)

        self.default_rtmidi_output_device = rtmidi_output_device

    def add_instrument(self, num_channels, bank_and_preset, soundfont=0,
                       midi_output_device=None, midi_output_name=None):
        midi_output_device = self.default_rtmidi_output_device if self.default_rtmidi_output_device is not None \
            else midi_output_device
        return CombinedMidiInstrument(self, num_channels, bank_and_preset, soundfont_id=self.soundfont_ids[soundfont],
                                      midi_output_device=midi_output_device, midi_output_name=midi_output_name)

    def initialize_fluidsynth(self, soundfont_paths, driver=None):
        # loads the soundfonts and gets the synth going
        self.synth = Synth()
        for soundfont_path in soundfont_paths:
            self.soundfont_ids.append(self.synth.sfload(soundfont_path))
        self.synth.start(driver=driver)

    def get_instruments_with_substring(self, word, avoid=None, soundfont_index=0):
        if 0 <= soundfont_index < len(self.soundfont_instrument_lists):
            instrument_list = self.soundfont_instrument_lists[soundfont_index]
            return [inst for i, inst in enumerate(instrument_list) if word.lower() in inst.name.lower() and
                    (avoid is None or avoid.lower() not in inst.name.lower())]
        return None


class CombinedMidiInstrument:

    def __init__(self, combined_midi_player, num_channels, bank_and_preset, soundfont_id=0,
                 midi_output_device=None, midi_output_name=None):
        assert isinstance(combined_midi_player, CombinedMidiPlayer)
        self.combined_midi_player = combined_midi_player
        self.channels = list(range(self.combined_midi_player.used_channels,
                                   self.combined_midi_player.used_channels + num_channels))
        self.num_channels = num_channels
        self.combined_midi_player.used_channels += num_channels
        self.bank_and_preset = bank_and_preset
        self.soundfont_id = soundfont_id

        self.max_pitch_bend = 2

        self.rt_simple_out = SimpleRtMidiOut(midi_output_device, midi_output_name)

        if fluidsynth_loaded:
            self.set_to_preset(*bank_and_preset)

    def set_to_preset(self, bank, preset):
        for i in self.channels:
            self.combined_midi_player.synth.program_select(i, self.soundfont_id, bank, preset)

    def note_on(self, chan, pitch, volume_from_0_to_1):
        """
        NB: for this and following commands, since a single instance of fluidsynth is running for all instruments,
        it we need to use the absolute channel when we call it 9I.. Each rt_midi output, on the other hand is local
        to the instrument, so no such conversion is necessary.
        """
        absolute_channel = self.channels[chan]
        velocity = int(volume_from_0_to_1 * 127)
        self.combined_midi_player.synth.noteon(absolute_channel, pitch, velocity)
        self.rt_simple_out.note_on(chan, pitch, velocity)

    def note_off(self, chan, pitch):
        absolute_channel = self.channels[chan]
        self.combined_midi_player.synth.noteon(absolute_channel, pitch, 0)  # note on call of 0 velocity implementation
        self.combined_midi_player.synth.noteoff(absolute_channel, pitch)  # note off call implementation
        self.rt_simple_out.note_off(chan, pitch)

    def pitch_bend(self, chan, bend_in_semitones):
        absolute_channel = self.channels[chan]
        directional_bend_value = int(bend_in_semitones / self.max_pitch_bend * 8192)
        # we can't have a directional pitch bend popping up to 8192, because we'll go one above the max allowed
        # on th other hand, -8192 is fine, since that will add up to zero
        directional_bend_value = max(-8192, min(directional_bend_value, 8191))
        # for some reason, pyFluidSynth takes a value from -8192 to 8191 and then adds 8192 to it
        self.combined_midi_player.synth.pitch_bend(absolute_channel, directional_bend_value)
        # rt_midi wants the normal value having added in 8192
        self.rt_simple_out.pitch_bend(chan, directional_bend_value + 8192)

    def set_max_pitch_bend(self, max_bend_in_semitones):
        """
        Sets the maximum pitch bend to the given number of semitones up and down for all tracks associated
        with this instrument. Note that, while this will definitely work with fluidsynth, the output of rt_midi
        must be being recorded already for this to affect subsequent pitch bend, which is slightly awkward.
        Also, in my experience, even then it may be ignored.
        :type max_bend_in_semitones: int
        :return: None
        """
        if not isinstance(max_bend_in_semitones, int):
            print("Max pitch bend must be an integer number of semitones.")
            return
        for chan in range(self.num_channels):
            absolute_channel = self.channels[chan]
            self.combined_midi_player.synth.cc(absolute_channel, 101, 0)
            self.rt_simple_out.cc(chan, 101, 0)
            self.combined_midi_player.synth.cc(absolute_channel, 100, 0)
            self.rt_simple_out.cc(chan, 100, 0)
            self.combined_midi_player.synth.cc(absolute_channel, 6, max_bend_in_semitones)
            self.rt_simple_out.cc(chan, 6, max_bend_in_semitones)
            self.combined_midi_player.synth.cc(absolute_channel, 100, 127)
            self.rt_simple_out.cc(chan, 100, 127)
            self.max_pitch_bend = max_bend_in_semitones

    def expression(self, chan, expression_from_0_to_1):
        absolute_channel = self.channels[chan]
        expression_val = int(expression_from_0_to_1 * 127)
        self.combined_midi_player.synth.cc(absolute_channel, 11, expression_val)
        self.rt_simple_out.expression(chan, expression_val)

