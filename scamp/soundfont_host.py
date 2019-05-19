from .utilities import resolve_relative_path, SavesToJSON, get_average_square_correlation
from .settings import playback_settings
from ._dependencies import fluidsynth, Sf2File
import logging
from collections import OrderedDict
import re


def get_soundfont_presets(which_soundfont="default"):
    which_soundfont = playback_settings.default_soundfont if which_soundfont == "default" else which_soundfont

    soundfont_path = playback_settings.named_soundfonts[which_soundfont] \
        if which_soundfont in playback_settings.named_soundfonts else which_soundfont

    if soundfont_path.startswith("./"):
        soundfont_path = resolve_relative_path("soundfonts/" + soundfont_path[2:])
    elif not soundfont_path.startswith("/"):
        soundfont_path = resolve_relative_path("soundfonts/" + soundfont_path)

    if Sf2File is None:
        raise ModuleNotFoundError("Cannot inspect soundfont presets; please install sf2utils.")

    # if we have sf2utils, load up the preset info from the soundfonts
    with open(soundfont_path, "rb") as sf2_file:
        sf2 = Sf2File(sf2_file)
        return sf2.presets


def print_soundfont_presets(which_soundfont="default"):
    print("PRESETS FOR {}".format("default ({})".format(playback_settings.default_soundfont)
                                  if which_soundfont == "default" else which_soundfont))
    for preset in get_soundfont_presets(which_soundfont):
        print("   {}".format(preset))


def get_soundfont_presets_with_substring(word, avoid=None, which_soundfont="default"):
    """
    Returns a list of Sf2Presets containing the given word

    :param word: string to match
    :param avoid: string to avoid matching
    :param which_soundfont: name of the soundfont to inspect
    """
    return [preset for preset in get_soundfont_presets(which_soundfont) if word.lower() in preset.name.lower()
            and (avoid is None or avoid.lower() not in preset.name.lower())]


def get_best_preset_match_for_name(name: str, which_soundfont="default"):
    """
    Does fuzzy string matching to find an appropriate preset for given name

    :param name: name of the instrument to find a preset for
    :param which_soundfont: which soundfont look in
    :return: a tuple of (Sf2Preset, match score)
    """
    if Sf2File is None:
        raise ModuleNotFoundError("Cannot iterate through soundfont presets; please install sf2utils.")
    best_preset_match = None
    best_preset_score = 0
    altered_name = name.lower()
    altered_name = _do_name_substitutions(altered_name)
    for scamp_soundfont_preset in get_soundfont_presets(which_soundfont):
        altered_preset_name = scamp_soundfont_preset.name.lower()
        altered_preset_name = _do_name_substitutions(altered_preset_name)
        score = get_average_square_correlation(altered_name, altered_preset_name)
        if score > best_preset_score:
            best_preset_score = score
            best_preset_match = scamp_soundfont_preset
    return best_preset_match, best_preset_score


class SoundfontHost(SavesToJSON):

    def __init__(self, soundfonts=(), audio_driver="default"):
        """
        A SoundfontHost hosts an instance of fluidsynth with one or several soundfonts loaded.
        It can be called upon to add or remove instruments from that synth

        :param soundfonts: one or several soundfonts to be loaded
        :param audio_driver: the audio driver to use
        """
        if isinstance(soundfonts, str):
            soundfonts = (soundfonts, )

        if fluidsynth is None:
            raise ModuleNotFoundError("FluidSynth not available.")

        self.audio_driver = playback_settings.default_audio_driver if audio_driver == "default" else audio_driver

        self.synth = fluidsynth.Synth()
        self.synth.start(driver=self.audio_driver)

        self.used_channels = 0  # how many channels have we already assigned to various instruments

        self.soundfont_ids = OrderedDict()  # mapping from soundfont names to the fluidsynth ids of loaded soundfonts
        self.soundfont_instrument_lists = {}

        for soundfont in soundfonts:
            self.load_soundfont(soundfont)

    def add_instrument(self, num_channels, bank_and_preset, soundfont=None):
        if soundfont is None:
            # if no soundfont is specified, use the first soundfont added
            soundfont_id = next(iter(self.soundfont_ids.items()))
        else:
            soundfont_id = self.soundfont_ids[soundfont]
        return SoundfontInstrument(self, num_channels, bank_and_preset, soundfont_id)

    def load_soundfont(self, soundfont):
        soundfont_path = resolve_soundfont_path(soundfont)

        if Sf2File is not None:
            # if we have sf2utils, load up the preset info from the soundfonts
            with open(soundfont_path, "rb") as sf2_file:
                sf2 = Sf2File(sf2_file)
                self.soundfont_instrument_lists[soundfont] = sf2.presets

        self.soundfont_ids[soundfont] = self.synth.sfload(soundfont_path)

    def to_json(self):
        return {"soundfonts": list(self.soundfont_ids.keys()), "audio_driver": self.audio_driver}

    @classmethod
    def from_json(cls, json_dict):
        return cls(**json_dict)


class SoundfontInstrument:

    def __init__(self, soundfont_host, num_channels, bank_and_preset, soundfont_id):
        """
        A SoundfontInstrument represents all the channels in the host dedicated to the same instrument
        On initialization, it loads the appropriate preset from the correct soundfont into those channels

        :param soundfont_host: a SoundfontHost
        :param num_channels: how many channels this instrument gets
        :param bank_and_preset: tuple consisting of the bank and preset to use
        :param soundfont_id: the fluidsynth id of the soundfont this instrument uses
        """

        assert isinstance(soundfont_host, SoundfontHost)
        self.soundfont_host = soundfont_host
        self.channels = list(range(self.soundfont_host.used_channels, self.soundfont_host.used_channels + num_channels))
        self.num_channels = num_channels
        self.soundfont_host.used_channels += num_channels
        self.bank_and_preset = bank_and_preset
        self.soundfont_id = soundfont_id
        self.max_pitch_bend = 2
        self.set_to_preset(*bank_and_preset)

    def set_to_preset(self, bank, preset):
        for i in self.channels:
            self.soundfont_host.synth.program_select(i, self.soundfont_id, bank, preset)

    def note_on(self, chan, pitch, volume_from_0_to_1):
        velocity = max(0, min(127, int(volume_from_0_to_1 * 127)))
        absolute_channel = self.channels[chan]
        self.soundfont_host.synth.noteon(absolute_channel, pitch, velocity)

    def note_off(self, chan, pitch):
        absolute_channel = self.channels[chan]
        self.soundfont_host.synth.noteon(absolute_channel, pitch, 0)  # note on call of 0 velocity implementation
        self.soundfont_host.synth.noteoff(absolute_channel, pitch)  # note off call implementation

    def pitch_bend(self, chan, bend_in_semitones):
        directional_bend_value = int(bend_in_semitones / self.max_pitch_bend * 8192)

        if directional_bend_value > 8192 or directional_bend_value < -8192:
            logging.warning("Attempted pitch bend beyond maximum range (default is 2 semitones). Call set_max_"
                            "pitch_bend to expand the range.")
        # we can't have a directional pitch bend popping up to 8192, because we'll go one above the max allowed
        # on the other hand, -8192 is fine, since that will add up to zero
        # However, notice above that we don't send a warning about going beyond max pitch bend for a value of exactly
        # 8192, since that's obnoxious and confusing. Better to just quietly clip it to 8191
        directional_bend_value = max(-8192, min(directional_bend_value, 8191))
        absolute_channel = self.channels[chan]
        # for some reason, pyFluidSynth takes a value from -8192 to 8191 and then adds 8192 to it
        self.soundfont_host.synth.pitch_bend(absolute_channel, directional_bend_value)

    def set_max_pitch_bend(self, max_bend_in_semitones):
        """
        Sets the maximum pitch bend to the given number of semitones up and down for all tracks associated
        with this instrument. Note that, while this will definitely work with fluidsynth, the output of rt_midi
        must be being recorded already for this to affect subsequent pitch bend, which is slightly awkward.
        Also, in my experience, even then it may be ignored.

        :type max_bend_in_semitones: int
        :return: None
        """
        if max_bend_in_semitones != int(max_bend_in_semitones):
            logging.warning("Max pitch bend must be an integer number of semitones. "
                            "The value of {} is being rounded up.".format(max_bend_in_semitones))
            max_bend_in_semitones = int(max_bend_in_semitones) + 1

        for chan in range(self.num_channels):
            absolute_channel = self.channels[chan]
            self.soundfont_host.synth.cc(absolute_channel, 101, 0)
            self.soundfont_host.synth.cc(absolute_channel, 100, 0)
            self.soundfont_host.synth.cc(absolute_channel, 6, max_bend_in_semitones)
            self.soundfont_host.synth.cc(absolute_channel, 100, 127)

        self.max_pitch_bend = max_bend_in_semitones

    def expression(self, chan, expression_from_0_to_1):
        expression_val = max(0, min(127, int(expression_from_0_to_1 * 127)))
        absolute_channel = self.channels[chan]
        self.soundfont_host.synth.cc(absolute_channel, 11, expression_val)


# ------------------------------------------- Utilities ------------------------------------------------

_preset_name_substitutions = [
    # voice types
    [r"\b(bs)\b", "bass"],
    [r"\b(bari)\b", "baritone"],
    [r"\b(alt)\b", "alto"],
    [r"\b(ten)\b", "tenor"],
    [r"\b(sop)\b", "soprano"],
    # winds
    [r"\b(flt)\b", "flute"],
    [r"\b(ob)\b", "oboe"],
    [r"\b(eng)\b", "english"],
    [r"\b(cl)\b", "clarinet"],
    [r"\b(bcl)\b", "bass clarinet"],
    [r"\b(bsn)\b", "bassoon"],
    [r"\b(cbn)\b", "contrabassoon"],
    [r"\b(sax)\b", "saxophone"],
    # brass
    [r"\b(tpt)\b", "trumpet"],
    [r"\b(hn)\b", "horn"],
    [r"\b(hrn)\b", "horn"],
    [r"\b(tbn)\b", "trombone"],
    [r"\b(tba)\b", "tuba"],
    # percussion / assorted
    [r"\b(timp)\b", "timpani"],
    [r"\b(perc)\b", "percussion"],
    [r"\b(xyl)\b", "xylophone"],
    [r"\b(hrp)\b", "harp"],
    [r"\b(pno)\b", "piano"],
    # strings
    [r"\b(str)\b", "strings"],
    [r"\b(vln)\b", "violin"],
    [r"\b(vla)\b", "viola"],
    [r"\b(vc)\b", "violoncello"],
    [r"\b(cello)\b", "violoncello"],
    [r"\b(cbs)\b", "contrabass"],
    # etc
    [r"\b(orch)\b", "orchestra"],
    [r"\b(std)\b", "standard"],
    [r"\b(gtr)\b", "guitar"],
    [r"\b(elec)\b", "electric"],
    [r"\b(pizz)\b", "pizzicato"],
    [r"(\bgold\b)", ""],  # fixes issue with "flute" getting matched with pan flute instead of flute gold
    [r"(\bmerlin\b)", ""],  # fixes issue with "piano" getting matched with piano 3 instead of piano merlin
    [r"(bassoon)\b", "fagotto"],  # this helps avoid confusion between contrabass and contrabassoon
]


def _do_name_substitutions(name: str):
    for match_string, replace_string in _preset_name_substitutions:
        match = re.search(match_string, name)
        if match:
            if len(match.groups()) > 0:
                name = name[:match.start(1)] + replace_string + name[match.end(1):]
            else:
                name = name[:match.start(0)] + replace_string + name[match.end(0):]
    return name


def resolve_soundfont_path(soundfont: str):
    """
    Consults playback settings and returns the path to the given soundfont

    :param soundfont: either the name of a named soundfont or an explicit soundfont path. Paths are resolved relatively
    unless they start with a slash.
    :return: an absolute path o the soundfont
    """
    soundfont_path = playback_settings.named_soundfonts[soundfont] \
        if soundfont in playback_settings.named_soundfonts else soundfont

    if soundfont_path.startswith("./"):
        soundfont_path = resolve_relative_path("soundfonts/" + soundfont_path[2:])
    elif not soundfont_path.startswith("/"):
        soundfont_path = resolve_relative_path("soundfonts/" + soundfont_path)
    return soundfont_path
