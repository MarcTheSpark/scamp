import threading
import time
import logging
from inspect import signature

from .recording_to_xml import save_to_xml_file as save_recording_to_xml

from .combined_midi_player import CombinedMidiPlayer, register_default_soundfont, \
    unregister_default_soundfont, get_default_soundfonts

from .simple_rtmidi_wrapper import get_available_midi_output_devices

from .performance import Performance, PerformancePart
from .parameter_curve import ParameterCurve

from .ensemble import Ensemble
from .instruments import PlaycorderInstrument, MidiPlaycorderInstrument

from .clock import Clock

# TODO: give the "properties" a playlength proportion, figure out how to make default playback properties of things like staccato, tenuto, slurs


class Playcorder:

    def __init__(self, soundfonts=None, audio_driver=None, midi_output_device=None):
        """

        :param soundfonts: the names / paths of the soundfonts this playcorder will use
        :param audio_driver: the driver used to output audio (if none, defaults to whatever fluidsynth chooses)
        :param midi_output_device: the default midi_output_device for outgoing midi streams. These can also be
        specified on a per-instrument basis, but this sets a global default. Defaults to creating virtual devices.
        """

        self._ensemble = None
        self.set_ensemble(Ensemble(soundfonts, audio_driver, midi_output_device))

        # Clock keeps track of time and can spawn subordinate clocks
        self.master_clock = Clock()
        self.recording_start_time = None

        # The Performance object created when we record
        self.performance = None

    @staticmethod
    def get_available_midi_output_devices():
        return get_available_midi_output_devices()

    @staticmethod
    def register_default_soundfont(name, soundfont_path):
        return register_default_soundfont(name, soundfont_path)

    @staticmethod
    def unregister_default_soundfont(name):
        return unregister_default_soundfont(name)

    @staticmethod
    def list_default_soundfonts():
        for a, b in get_default_soundfonts().items():
            print("{}: {}".format(a, b))

    # ----------------------------------- Clock Stuff --------------------------------

    def time(self):
        return self.master_clock.time()

    def fork(self, process_function):
        num_params = len(signature(process_function).parameters)
        if num_params > 1:
            logging.warning("The function passed to fork should take one argument, which is the clock used for that "
                            "thread. Additional arguments are not used.")
        elif num_params == 0:
            logging.warning("The function passed to fork must take one argument, which is the clock used for that "
                            "thread, but none were given.")
            return
        return self.master_clock.fork(process_function)

    # used for a situation where all parts are played from a single thread
    def wait(self, seconds):
        self.master_clock.wait(seconds)

    def wait_forever(self):
        while True:
            self.wait(1.0)

    # --------------------------------- Ensemble Stuff -------------------------------

    @property
    def ensemble(self):
        return self._ensemble

    @ensemble.setter
    def ensemble(self, ensemble: Ensemble):
        self.set_ensemble(ensemble)

    def set_ensemble(self, ensemble: Ensemble):
        self._ensemble = ensemble
        self._ensemble.host_playcorder = self

    def get_instruments_with_substring(self, word, avoid=None, soundfont_index=0):
        return self._ensemble.midi_player.get_instruments_with_substring(word, avoid=avoid,
                                                                         soundfont_index=soundfont_index)

    def add_part(self, instrument):
        assert isinstance(instrument, PlaycorderInstrument)
        return self._ensemble.add_part(instrument)

    def add_midi_part(self, name=None, preset=(0, 0), soundfont_index=0, num_channels=8,
                      midi_output_device=None, midi_output_name=None):
        return self._ensemble.add_midi_part(name, preset, soundfont_index, num_channels,
                                            midi_output_device, midi_output_name)

    def add_silent_part(self, name=None):
        return self._ensemble.add_silent_part(name)

    def save_ensemble_to_json(self, filepath):
        import json
        with open(filepath, "w") as file:
            json.dump(self._ensemble.to_json(), file)

    def load_ensemble_from_json(self, filepath):
        import json
        with open(filepath, "r") as file:
            self.set_ensemble(Ensemble.from_json(json.load(file)))

    # ----------------------------- Modifying MIDI Settings --------------------------

    @property
    def audio_driver(self):
        return self._ensemble.audio_driver

    @audio_driver.setter
    def audio_driver(self, audio_driver):
        self._ensemble.audio_driver = audio_driver

    @property
    def default_midi_output_device(self):
        return self._ensemble.default_midi_output_device

    @default_midi_output_device.setter
    def default_midi_output_device(self, device):
        self._ensemble.default_midi_output_device = device

    def load_soundfont(self, soundfont):
        self._ensemble.load_soundfont(soundfont)

    # --------------------------------- Recording Stuff -------------------------------

    def start_recording(self, which_parts=None):
        self.recording_start_time = self.master_clock._t
        which_parts = self._ensemble.instruments if which_parts is None else which_parts
        self.performance = Performance()
        # set a performance_part for each instrument
        for instrument in which_parts:
            new_part = self.performance.new_part(instrument)
            instrument.performance_part = new_part

    def is_recording(self):
        return self.recording_start_time is not None

    def recording_time(self):
        return self.time() - self.recording_start_time

    def stop_recording(self):
        for part in self.performance.parts:
            instrument = part.instrument
            instrument.end_all_notes()
            instrument.performance_part = None
        self.recording_start_time = None
        return self.performance

    # ---------------------------------------- SAVING TO XML ----------------------------------------------

    def save_to_xml_file(self, file_name, measure_schemes=None, time_signature="4/4", tempo=60, divisions=8,
                         max_indigestibility=4, simplicity_preference=0.5, title=None, composer=None,
                         separate_voices_in_separate_staves=True, show_cent_values=True, add_sibelius_pitch_bend=False,
                         max_overlap=0.001):
        """

        :param file_name: The name of the file, duh
        :param measure_schemes: list of measure schemes, which include time signature and quantization preferences. If
        None, then we assume a single persistent measure scheme based on the given  time_signature, tempo, divisions,
        max_indigestibility, and simplicity_preference
        :param time_signature: formatted as a tuple e.g. (4, 4) or a string e.g. "4/4"
        :param tempo: in bpm
        :param divisions: For beat quantization purposes. This parameter can take several forms. If an integer is given,
        then all beat divisions up to that integer are allowed, providing that the divisor indigestibility is less than
        the max_indigestibility. Alternatively, a list of allowed divisors can be given. This is useful if we know
        ahead of time exactly how we will be dividing the beat. Each divisor will be assigned an undesirability based
        on its indigestibility; however these can be overridden by passing a list of tuples formatted
        [(divisor1, undesirability1), (divisor2, undesirability2), etc... ] to this parameter.
        :param max_indigestibility: when an integer is passed to the divisions parameter, all beat divisions up to that
        integer that have indigestibility less than max_indigestibility are allowed
        :param simplicity_preference: ranges 0 - whatever. A simplicity_preference of 0 means, all beat divisions are
        treated equally; a 7 is as good as a 4. A simplicity_preference of 1 means that the most desirable division
        is left alone, the most undesirable division gets its error doubled, and all other divisions are somewhere in
        between. Simplicity preference can be greater than 1, in which case the least desirable division gets its
        error multiplied by (simplicity_preference + 1).
        :param title: duh
        :param composer: duh
        :param separate_voices_in_separate_staves: where notes in a part overlap, they are placed in separate staves if
        true and separate voices of the same staff if false
        :param show_cent_values: adds text displaying the cent deviations of a microtonal pitch
        :param add_sibelius_pitch_bend: adds in hidden text used to send midi pitch bend messages in sibelius when given
        a microtonal pitch.
        :param max_overlap: used to determine when two simultaneous notes form a chord
        """
        part_recordings = [this_part.recording for this_part in self.parts_recorded]
        part_names = [this_part.name for this_part in self.parts_recorded]
        save_recording_to_xml(part_recordings, part_names, file_name, measure_schemes=measure_schemes,
                              time_signature=time_signature, tempo=tempo, divisions=divisions,
                              max_indigestibility=max_indigestibility, simplicity_preference=simplicity_preference,
                              title=title, composer=composer,
                              separate_voices_in_separate_staves=separate_voices_in_separate_staves,
                              show_cent_values=show_cent_values, add_sibelius_pitch_bend=add_sibelius_pitch_bend,
                              max_overlap=max_overlap)