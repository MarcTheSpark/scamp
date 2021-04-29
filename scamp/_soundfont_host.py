#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  This file is part of SCAMP (Suite for Computer-Assisted Music in Python)                      #
#  Copyright © 2020 Marc Evanstein <marc@marcevanstein.com>.                                     #
#                                                                                                #
#  This program is free software: you can redistribute it and/or modify it under the terms of    #
#  the GNU General Public License as published by the Free Software Foundation, either version   #
#  3 of the License, or (at your option) any later version.                                      #
#                                                                                                #
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;     #
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     #
#  See the GNU General Public License for more details.                                          #
#                                                                                                #
#  You should have received a copy of the GNU General Public License along with this program.    #
#  If not, see <http://www.gnu.org/licenses/>.                                                   #
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #

from .utilities import resolve_path, SavesToJSON, get_average_square_correlation
from .settings import playback_settings
from ._dependencies import fluidsynth, Sf2File
import logging
from collections import OrderedDict
import re
import os.path
import atexit
import functools
import clockblocks
import threading
import time
import wave


# ------------------------------------------ Synth that records output -----------------------------------------------

class PlayAndRecSynth(fluidsynth.Synth):

    """
    A subclass of :class:`fluidsynth.Synth` that create an additional Synth object to which every call is mirrored,
    and pulls out the samples to save to a wave file. The idea is that it is a drop-in replacement for Synth that
    has the side effect of saving to a file.

    :param recording_file_path: the file to save recorded output to
    :param gain: see :class:`fluidsynth.Synth`
    :param samplerate: see :class:`fluidsynth.Synth`
    :param channels: see :class:`fluidsynth.Synth`
    :param timer_func: function used to measure what time it is
    :param time_range: the time range that we want to record of the output
    """

    def __init__(self, recording_file_path, gain=0.2, samplerate=44100, channels=256, timer_func=time.time,
                 time_range=(0, float("inf")), **kwargs):
        super().__init__(gain, samplerate, channels, **kwargs)
        # Note: this import is here because `fluidsynth.raw_audio_string` imports numpy after SCAMP has started
        # playback, an expensive operation that disrupts playback. By importing here, we front-load that.
        import numpy
        self.start_time = timer_func()
        self.timer_func = timer_func
        self.samplerate = samplerate
        self.sample_range = int(time_range[0] * samplerate), \
                            int(time_range[1] * samplerate) if time_range[1] != float("inf") else float("inf")
        # This is the parallel Synth object used for drawing out samples and saving them to a file
        self.recording_synth = fluidsynth.Synth(gain, samplerate, channels, **kwargs)
        self.current_sample = 0
        self.sample_queue = []
        self.wave_file = None
        self.recording = False
        self.recording_thread = None
        self.start_recording(recording_file_path)

    def start_recording(self, file_path):
        self.wave_file = wave.open(file_path, 'wb')
        self.wave_file.setnchannels(2)
        self.wave_file.setsampwidth(2)
        self.wave_file.setframerate(44100)
        self.recording = True
        self.recording_thread = threading.Thread(target=self.record_thread, daemon=True)
        self.recording_thread.start()
        atexit.register(self.stop_recording)

    def record_thread(self):
        sample_num = 0
        while self.recording or len(self.sample_queue):
            while len(self.sample_queue) > 0:
                new_samps = self.sample_queue.pop(0).reshape(-1, 2)
                end_sample_num = sample_num + len(new_samps)
                num_beginning_samples_to_skip = self.sample_range[0] - sample_num \
                    if self.sample_range[0] > sample_num else 0
                num_ending_samples_to_skip = end_sample_num - self.sample_range[1] \
                    if end_sample_num > self.sample_range[1] else 0
                if num_beginning_samples_to_skip + num_ending_samples_to_skip < len(new_samps):
                    self.wave_file.writeframes(
                        new_samps[num_beginning_samples_to_skip:len(new_samps) - num_ending_samples_to_skip].tobytes())
                if end_sample_num > self.sample_range[1]:
                    self.sample_queue.clear()
                    self.stop_recording()
                    break
                sample_num = end_sample_num
            if self.recording:
                time.sleep(0.1)
        self.wave_file.close()

    def stop_recording(self):
        if self.recording:
            # add some blank samples at the end (for reverb tails and such)
            if self.current_sample < self.sample_range[1]:
                # if we're stopping but the sample range says keep going (probably because we exited the script before
                # reaching that sample) then we append extra samples up to the top of the sample range, or just an extra
                # second of samples (self.samplerate) in the case that the upper bound was set to infinite
                extra_samples = self.sample_range[1] - self.current_sample if self.sample_range[1] != float("inf") \
                    else self.samplerate
                self.sample_queue.append(self.recording_synth.get_samples(extra_samples))
            self.recording = False
            if threading.current_thread() is not self.recording_thread:
                # sometimes this is called at the end by atexit and we want to make sure we finish writing all
                # the samples. When it's called from record_thread, this is irrelevant since it's on the same thread
                self.recording_thread.join()


synth_lock = threading.Lock()


def _record_as_well(f):
    """
    Decorator that is used to wrap the various Synth functions, which makes the same functions get called on the
    recording synth. Also draws out the new samples from the recording synth and adds them them to self.sample_queue.
    (The "record_thread" above then reads from this sample queue on a separate thread and writes to a file.)
    """
    @functools.wraps(f)
    def wrapped_method(self, *args, **kwargs):
        with synth_lock:
            return_value = f(self, *args, **kwargs)
            current_sample = int((self.timer_func() - self.start_time) * self.samplerate)
            num_new_samples = current_sample - self.current_sample
            self.current_sample = current_sample
            if self.wave_file is not None:

                if num_new_samples > 0:
                    self.sample_queue.append(self.recording_synth.get_samples(num_new_samples))

                f(self.recording_synth, *args, **kwargs)
        return return_value
    return wrapped_method


PlayAndRecSynth.sfload = _record_as_well(PlayAndRecSynth.sfload)
PlayAndRecSynth.program_select = _record_as_well(PlayAndRecSynth.program_select)
PlayAndRecSynth.noteon = _record_as_well(PlayAndRecSynth.noteon)
PlayAndRecSynth.noteoff = _record_as_well(PlayAndRecSynth.noteoff)
PlayAndRecSynth.cc = _record_as_well(PlayAndRecSynth.cc)
PlayAndRecSynth.pitch_bend = _record_as_well(PlayAndRecSynth.pitch_bend)


# ------------------------------------------ Main SoundfontHost classes ----------------------------------------------


class SoundfontHost(SavesToJSON):

    def __init__(self, soundfonts=(), audio_driver="default",
                 recording_file_path=None, recording_time_range=(0, float("inf"))):
        """
        A SoundfontHost hosts an instance of fluidsynth with one or several soundfonts loaded.
        It can be called upon to add or remove instruments from that synth

        :param soundfonts: one or several soundfonts to be loaded
        :param audio_driver: the audio driver to use
        :param recording_file_path: if not None, save the playback to a .wav file with this path
        :param recording_time_range: the time range of playback to save (defaults to all)
        """
        if isinstance(soundfonts, str):
            soundfonts = (soundfonts, )

        if fluidsynth is None:
            raise ModuleNotFoundError("FluidSynth not available.")

        self.audio_driver = playback_settings.default_audio_driver if audio_driver == "default" else audio_driver

        if recording_file_path:
            clock = clockblocks.current_clock()

            def _timer_func():
                if clock is None:
                    return time.time()
                else:
                    if hasattr(clock.master, 'unsynced_time'):
                        return max(clock.master.unsynced_time, clock.time_in_master())
                    else:
                        return clock.time_in_master()
            self.synth = PlayAndRecSynth(recording_file_path,
                                         timer_func=_timer_func,
                                         time_range=recording_time_range)
        else:
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
        soundfont_path = resolve_soundfont(soundfont)

        if Sf2File is not None:
            # if we have sf2utils, load up the preset info from the soundfonts
            with open(soundfont_path, "rb") as sf2_file:
                sf2 = Sf2File(sf2_file)
                self.soundfont_instrument_lists[soundfont] = sf2.presets

        self.soundfont_ids[soundfont] = self.synth.sfload(soundfont_path)

    def _to_dict(self) -> dict:
        return {"soundfonts": list(self.soundfont_ids.keys()), "audio_driver": self.audio_driver}

    @classmethod
    def _from_dict(cls, json_dict):
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
        velocity = int(playback_settings.soundfont_volume_to_velocity_curve.value_at(volume_from_0_to_1))
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

    def cc(self, chan, cc_number, expression_from_0_to_1):
        expression_val = max(0, min(127, int(expression_from_0_to_1 * 127)))
        absolute_channel = self.channels[chan]
        self.soundfont_host.synth.cc(absolute_channel, cc_number, expression_val)

    def expression(self, chan, expression_from_0_to_1):
        self.cc(chan, 11, expression_from_0_to_1)


# ------------------------------------------- Utilities ------------------------------------------------


def resolve_soundfont(soundfont: str) -> str:
    """
    Consults playback settings and returns the path to the given soundfont

    :param soundfont: either the name of a named soundfont or an explicit soundfont path. Paths starting with "/" are
        absolute, "~/" are relative to the user home directory, "%PKG/" are relative to the scamp package root, and
        unprefixed paths are tested against all of the search paths defined in playback_settings.soundfont_search_paths
        and then against the current working directory.
    :return: an absolute path to the soundfont
    """
    soundfont_path = playback_settings.named_soundfonts[soundfont] \
        if soundfont in playback_settings.named_soundfonts else soundfont

    path = _resolve_soundfont_path(soundfont_path)
    if os.path.exists(path):
        return path
    elif not path.endswith(".sf2"):
        path = _resolve_soundfont_path(soundfont_path + ".sf2")
        if os.path.exists(path):
            return path
    if soundfont in playback_settings.named_soundfonts:
        raise ValueError("Named soundfont \"{}\" was resolved to \"{}\", which did not exist.".format(soundfont, path))
    else:
        raise ValueError("\"{}\" was not recognized either as a named "
                         "soundfont or as a valid path to a soundfont".format(soundfont))


def _resolve_soundfont_path(soundfont_path: str) -> str:
    """Implementation minus checking for both with and without .sf2 extension."""

    if soundfont_path.startswith(("/", "~/", "%PKG/")) or soundfont_path[1:].startswith(":\\"):
        # Absolute soundfont path
        return resolve_path(soundfont_path)
    else:
        # Relative to one of the search paths defined in the settings
        for search_path in playback_settings.soundfont_search_paths:
            resolved_search_path = resolve_path(search_path)
            if os.path.exists(os.path.join(resolved_search_path, soundfont_path)):
                return os.path.join(resolved_search_path, soundfont_path)

    return os.path.join(os.getcwd(), soundfont_path)


def get_soundfont_presets(which_soundfont="default"):
    which_soundfont = playback_settings.default_soundfont if which_soundfont == "default" else which_soundfont

    soundfont_path = resolve_soundfont(which_soundfont)

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
