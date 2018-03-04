from .playcorder_utilities import resolve_relative_path

fluidsynth_loaded = False
try:
    from .thirdparty.fluidsynth import Synth
    fluidsynth_loaded = True
except ImportError:
    "Fluidsynth could not be loaded; synth output will not be available."

rtmidi_loaded = False
try:
    import rtmidi
    rtmidi_loaded = True
except ImportError:
    "python-rtmidi was not found; midi output will not be available."

sf2utils_loaded = False
try:
    from sf2utils.sf2parse import Sf2File
    sf2utils_loaded = True
except ImportError:
    "sf2utils was not found; info about soundfont presets will not be available."


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


def get_best_name_match(names_list, desired_name):
    """
    Looks initially for first exact case-sensitive match for desired_name in names_list. Then looks for
    first case insensitive match. Then looks for anything containing desired_name (case insensitive).
    Outputs None if this all fails
    :param names_list: list of names to search through
    :param desired_name: name to match
    :return: str of best match to desired name in names_list
    """
    if desired_name in names_list:
        return names_list.index(desired_name)
    lower_case_list = [s.lower() for s in names_list]
    lower_case_desired_name = desired_name.lower()
    if lower_case_desired_name in lower_case_list:
        return lower_case_list.index(lower_case_desired_name)
    for lower_case_name in lower_case_list:
        if lower_case_desired_name in lower_case_name:
            return lower_case_list.index(lower_case_name)
    return None


class CombinedMidiPlayer:

    def __init__(self, soundfonts=None):

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

    def __init__(self, combined_midi_player, num_channels, bank_and_preset=None, soundfont_id=0,
                 midi_output_device=None, midi_output_name=None):
        assert isinstance(combined_midi_player, CombinedMidiPlayer)
        self.combined_midi_player = combined_midi_player
        self.channels = list(range(self.combined_midi_player.used_channels,
                                   self.combined_midi_player.used_channels + num_channels))
        self.bank_and_preset = bank_and_preset
        self.soundfont_id = soundfont_id

        if rtmidi_loaded:
            self.midiout = rtmidi.MidiOut()
            if isinstance(midi_output_device, int):
                self.midiout.open_port(midi_output_device, name=midi_output_name)
            else:
                available_ports = self.midiout.get_ports()
                chosen_output = get_best_name_match(available_ports, midi_output_device)
                if chosen_output is not None:
                    self.midiout.open_port(chosen_output, name=midi_output_name)
                else:
                    self.midiout.open_virtual_port(name=midi_output_name)

        if fluidsynth_loaded:
            self.set_to_preset(*bank_and_preset)

    def set_to_preset(self, bank, preset):
        for i in self.channels:
            self.combined_midi_player.synth.program_select(i, self.soundfont_id, bank, preset)

    def note_on(self, chan, pitch, volume_from_0_to_1):
        absolute_channel = self.channels[chan]
        self.combined_midi_player.synth.noteon(absolute_channel, pitch, int(volume_from_0_to_1 * 127))

    def note_off(self, chan, pitch):
        absolute_channel = self.channels[chan]
        self.combined_midi_player.synth.noteon(absolute_channel, pitch, 0)  # note on call of 0 velocity implementation
        self.combined_midi_player.synth.noteoff(absolute_channel, pitch)  # note off call implementation

    def set_pitch_bend(self, chan, bend_in_semitones):
        absolute_channel = self.channels[chan]
        pitch_bend_val = int(bend_in_semitones*4096)
        self.combined_midi_player.synth.pitch_bend(absolute_channel, pitch_bend_val)

    def set_expression(self, chan, expression_from_0_to_1):
        absolute_channel = self.channels[chan]
        self.combined_midi_player.synth.cc(absolute_channel, 11, int(expression_from_0_to_1 * 127))
