import threading
import time

from .recording_to_xml import save_to_xml_file as save_recording_to_xml
from .recording_to_xml import separate_into_non_overlapping_voices, quantize_recording
from .measures_beats_notes import *
from midiutil.MidiFile import MIDIFile
from .thirdparty.fluidsynth import Synth
# from .localfluidsynth import localfluidsynth as fluidsynth  ## if a self-contained fluidsynth is being used
from .playcorder_utilities import resolve_relative_path, round_to_multiple, make_flat_list


# TODO: SOMETHING GOES WRONG WHEN THERE ARE LIKE 3 STAVES, and they get disconnected
# TODO: SPECIFY MAX VOICES PER STAFF
# TODO: SPECIFY MOST APPROPRIATE CLEF FOR EACH STAFF OF EACH MEASURE

f = open(resolve_relative_path('thirdparty/soundfonts/defaultSoundfonts.txt'), 'r')
_defaultSoundfonts = {x.split(" ")[0]: x.split(" ")[1] for x in f.read().split("\n")}
for x in _defaultSoundfonts:
    if _defaultSoundfonts[x].startswith("./"):
        _defaultSoundfonts[x] = resolve_relative_path("thirdparty/soundfonts/"+_defaultSoundfonts[x][2:])
    elif not _defaultSoundfonts[x].startswith("/"):
        _defaultSoundfonts[x] = resolve_relative_path("thirdparty/soundfonts/"+_defaultSoundfonts[x])
f.close()


class Playcorder:

    def __init__(self, soundfont_path=None, channels_per_part=50, additional_soundfont_paths=None, driver=None):
        """

        :param soundfont_path: if we are using midi playback, the soundfont path
        :param channels_per_part: in fluidsynth midi playback,  each new note is played through a separate "channel".
        This sets the number of channels used by each instrument before recycling. Essentially a max # of voices.
        """

        # list of the current instruments used by this playcorder
        self.instruments = []

        # --- MIDI setup, if necessary ---
        self.channels_per_part = channels_per_part
        self.used_channels = 0  # how many channels have we already assigned to various instruments
        self.synth = None
        self.soundfont_id = None  # the id of a loaded soundfont
        self.additional_soundfont_ids = []
        if soundfont_path is not None:
            if soundfont_path in _defaultSoundfonts:
                soundfont_path = _defaultSoundfonts[soundfont_path]
            self.initialize_fluidsynth(soundfont_path, additional_soundfont_paths=additional_soundfont_paths,
                                       driver=driver)

        # construct a list of all the instruments available in the soundfont, for reference access
        self.instrument_list = None
        if soundfont_path is not None:
            from sf2utils.sf2parse import Sf2File
            with open(soundfont_path, "rb") as sf2_file:
                sf2 = Sf2File(sf2_file)
                self.instrument_list = sf2.presets

        self.additional_soundfont_instrument_lists = []
        if additional_soundfont_paths is not None:
            for soundfont_path in additional_soundfont_paths:
                from sf2utils.sf2parse import Sf2File
                with open(soundfont_path, "rb") as sf2_file:
                    sf2 = Sf2File(sf2_file)
                    self.additional_soundfont_instrument_lists.append(sf2.presets)

        # --- Recording Setup ---
        # parts_being_recorded is a list of parts being recorded if recording otherwise it's None
        self.parts_being_recorded = None
        # once recording stops parts_recorded stores the parts that were recorded
        self.parts_recorded = None
        # recording_start_time is used if using time.time() as time
        # time_passed is used if manually recording time
        self.recording_start_time = None
        self.time_passed = None

    def initialize_fluidsynth(self, soundfont_path, additional_soundfont_paths=None, driver=None):
        # loads the soundfont and gets the synth going
        self.synth = Synth()
        self.soundfont_id = self.synth.sfload(soundfont_path)
        if additional_soundfont_paths is not None:
            for additional_soundfont_path in additional_soundfont_paths:
                self.additional_soundfont_ids.append(self.synth.sfload(additional_soundfont_path))
        self.synth.start(driver=driver);

    def get_instruments_with_substring(self, word, avoid=None, soundfont_index=0):
        instrument_list = self.instrument_list if soundfont_index == 0 \
            else None if soundfont_index > len(self.additional_soundfont_instrument_lists) \
            else self.additional_soundfont_instrument_lists[soundfont_index-1]

        if instrument_list is None:
            return None
        return [inst for i, inst in enumerate(instrument_list) if word.lower() in inst.name.lower() and
                (avoid is None or avoid.lower() not in inst.name.lower())]

    def add_part(self, instrument):
        assert isinstance(instrument, PlaycorderInstrument)
        if not hasattr(instrument, "name") or instrument.name is None:
            instrument.name = "Track " + str(len(self.instruments) + 1)
        instrument.host_playcorder = self
        self.instruments.append(instrument)

    def add_midi_part(self, preset, name=None, soundfont_index=0):
        """
        Constructs a MidiPlaycorderInstrument, adds it to the Playcorder, and returns it
        :param preset: if an int, assumes bank #0; can also be a tuple of form (bank, preset)
        :rtype : MidiPlaycorderInstrument
        """
        if self.synth is None:
            raise Exception("Fluidsynth not initialized")

        if name is None:
            name = "Track " + str(len(self.instruments) + 1)

        assert soundfont_index <= len(self.additional_soundfont_ids)
        soundfont_id = self.soundfont_id if soundfont_index == 0 else self.additional_soundfont_ids[soundfont_index-1]

        if isinstance(preset, int):
            # if just an int, assume bank 0 and that's the preset
            instrument = MidiPlaycorderInstrument(self.synth, soundfont_id, (0, preset), self.used_channels,
                                                  self.channels_per_part, self, name)
        else:
            # inst_num is a bank, preset pair
            instrument = MidiPlaycorderInstrument(self.synth, soundfont_id, preset, self.used_channels,
                                                  self.channels_per_part, self, name)

        self.used_channels += self.channels_per_part
        self.add_part(instrument)
        return instrument

    def add_silent_part(self, name=None):
        """
        Constructs a SilentPlaycorderInstrument, adds it to the Playcorder, and returns it
        :rtype : SilentPlaycorderInstrument
        """
        name = "Track " + str(len(self.instruments) + 1) if name is None else name
        instrument = PlaycorderInstrument(self, name=name)
        self.add_part(instrument)
        return instrument

    # ----------------------------------- Recording ----------------------------------

    def record_note(self, instrument, pitch, volume, length, start_delay=0,
                    variant_dictionary=None, start_time=None, written_length=None):
        if self.parts_being_recorded is not None and instrument in self.parts_being_recorded:
            if start_time is not None:
                note_start_time = start_time
            else:
                note_start_time = self.get_time_passed() + start_delay
            instrument.recording.append(MPNote(start_time=note_start_time,
                                               length=length if written_length is None else written_length,
                                               pitch=pitch, volume=volume, variant=variant_dictionary, tie=None))

    def get_time_passed(self):
        if self.parts_being_recorded is not None:
            if self.time_passed is not None:
                # manually logging time, so use time_passed
                return self.time_passed
            else:
                # not manually logging time; just measure from the start time
                return time.time()-self.recording_start_time

    def start_recording(self, which_parts=None, manual_time=False):
        if manual_time:
            self.time_passed = 0
        else:
            self.recording_start_time = time.time()
        self.parts_being_recorded = self.instruments if which_parts is None else which_parts
        # the "score" for each part is recorded as an attribute of that part called "recording"
        for instrument in self.parts_being_recorded:
            instrument.recording = []

    def stop_recording(self):
        for part in self.parts_being_recorded:
            part.end_all_notes()
        self.parts_recorded = self.parts_being_recorded
        self.parts_being_recorded = None
        self.time_passed = None
        self.recording_start_time = None

    # used for a situation where all parts are played from a single thread
    def wait(self, seconds):
        time.sleep(seconds)
        if self.time_passed is not None:
            self.time_passed += seconds

    # used for a situation where time is recorded manually, but there may be multiple threads,
    # only one of which registers time passed.
    def register_time_passed(self, seconds):
        if self.time_passed is not None:
            self.time_passed += seconds

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
        from marcpy.utilities import save_object
        save_object((part_recordings, part_names, file_name), "bob.pk")
        save_recording_to_xml(part_recordings, part_names, file_name, measure_schemes=measure_schemes,
                              time_signature=time_signature, tempo=tempo, divisions=divisions,
                              max_indigestibility=max_indigestibility, simplicity_preference=simplicity_preference,
                              title=title, composer=composer,
                              separate_voices_in_separate_staves=separate_voices_in_separate_staves,
                              show_cent_values=show_cent_values, add_sibelius_pitch_bend=add_sibelius_pitch_bend,
                              max_overlap=max_overlap)

    # ---------------------------------------- SAVING TO MIDI ----------------------------------------------
    # TODO: Fix this pile of crap

    @staticmethod
    def get_good_tempo_choice(pc_note_list, max_tempo=200, max_tempo_to_divide_to=300, goal_tempo=80):
        min_beat_length = 60.0 / max_tempo_to_divide_to
        total_length = max([(pc_note.start_time + pc_note.length) for pc_note in pc_note_list])
        divisor = 1

        best_beat_length = None
        best_error = float("inf")
        while total_length / divisor >= min_beat_length:
            beat_length = total_length / divisor
            total_squared_error = 0.0
            for pc_note in pc_note_list:
                total_squared_error += \
                    (pc_note.start_time - round_to_multiple(pc_note.start_time, beat_length/4.0)) ** 2

            total_squared_error *= (abs((60.0/beat_length) - goal_tempo)/50 + 1.0)
            if total_squared_error < best_error:
                best_error = total_squared_error
                best_beat_length = beat_length
            divisor += 1

        best_tempo = 60 / best_beat_length
        while best_tempo > max_tempo:
            best_tempo /= 2
        return best_tempo

    # TODO: Be able to add time signatures at any point, tempo changes at any point
    def save_to_midi_file(self, file_name, tempo=60, beat_length=1.0, divisions=8, max_indigestibility=4,
                          simplicity_preference=0.5, beat_max_overlap=0.01, quantize=True,
                          round_pitches=True, guess_tempo=False):
        if guess_tempo:
            flattened_recording = make_flat_list(
                [part.recording for part in self.parts_recorded]
            )
            tempo = Playcorder.get_good_tempo_choice(flattened_recording)

        if quantize:
            beat_scheme = BeatQuantizationScheme(
                tempo, beat_length, divisions=divisions, max_indigestibility=max_indigestibility,
                simplicity_preference=simplicity_preference
            )

            parts = [separate_into_non_overlapping_voices(
                quantize_recording(part.recording, [beat_scheme])[0], beat_max_overlap
            ) for part in self.parts_recorded]
        else:
            parts = [separate_into_non_overlapping_voices(
                part.recording, beat_max_overlap
            ) for part in self.parts_recorded]

        midi_file = MIDIFile(sum([len(x) for x in parts]), adjust_origin=False)

        current_track = 0
        for which_part, part in enumerate(parts):
            current_voice = 0
            for voice in part:
                midi_file.addTrackName(current_track, 0, self.parts_recorded[which_part].name + " " + str(current_voice + 1))
                midi_file.addTempo(current_track, 0, tempo)

                for pc_note in voice:
                    assert isinstance(pc_note, MPNote)
                    pitch_to_notate = int(round(pc_note.pitch)) if round_pitches else pc_note.pitch
                    midi_file.addNote(current_track, 0, pitch_to_notate, pc_note.start_time,
                                      pc_note.length, int(pc_note.volume*127))
                current_track += 1
                current_voice += 1

        bin_file = open(file_name, 'wb')
        midi_file.writeFile(bin_file)
        bin_file.close()


class PlaycorderInstrument:

    def __init__(self, host_playcorder=None, name=None):
        """
        This is the parent class used all kinds of instruments used within a playcorder. The most basic one, below,
        called a MidiPlaycorderInstrument, uses fluidsynth to playback sounds from a soundfont
        :param host_playcorder: The playcorder that this instrument acts within
        :param name: The name of this instrument (used later in labeling parts in output)
        """
        assert isinstance(host_playcorder, Playcorder)
        self.host_playcorder = host_playcorder
        self.name = name
        self.notes_started = []   # each entry goes (note_id, pitch, volume, start_time, variant_dictionary)
        self.render_info = {}

    # ------------------ Methods to be overridden by subclasses ------------------

    def _do_play_note(self, pitch, volume, length, start_delay, variant_dictionary):
        # Does the actual sonic implementation of playing a note
        pass

    def _do_start_note(self, pitch, volume, variant_dictionary=None):
        # Does the actual sonic implementation of starting a note
        # should return the note_id, which is used to keep track of the note
        return 0

    def _do_end_note(self, note_id):
        # Does the actual sonic implementation of ending a the note with the given id
        pass

    def change_note_pitch(self, note_id, new_pitch):
        # Changes the pitch of the note with the given id
        pass

    def change_note_volume(self, note_id, new_volume):
        # Changes the expression of the note with the given id
        pass

    # ------------------------- "Public" Playback Methods -------------------------

    def play_note(self, pitch, volume, length, start_delay=0, variant_dictionary=None, play_length=None):
        threading.Thread(target=self._do_play_note, args=(pitch, volume, length if play_length is None else play_length,
                                                          start_delay, variant_dictionary)).start()

        # record the note in the hosting playcorder, if it's recording
        if self.host_playcorder and self.host_playcorder.get_time_passed() is not None:
            # handle the case where an envelope is given as an argument
            if hasattr(pitch, "__len__"):
                if hasattr(pitch[0], "__len__"):
                    pitch = pitch[0][0]
                else:
                    pitch = pitch[0]
            if hasattr(volume, "__len__"):
                if hasattr(volume[0], "__len__"):
                    volume = max(volume[0])
                else:
                    volume = max(volume)
            self.host_playcorder.record_note(self, pitch, volume, length,
                                             start_delay, variant_dictionary=variant_dictionary)

    def start_note(self, pitch, volume, variant_dictionary=None):
        note_id = self._do_start_note(pitch, volume, variant_dictionary)
        self.notes_started.append((note_id, pitch, volume, self.host_playcorder.get_time_passed(), variant_dictionary))
        # returns the note_id as a reference, in case we want to change pitch mid playback
        return note_id

    def end_note(self, note_id=None):
        note_to_end = None
        if note_id is not None:
            # find the note referred to in the notes_started list
            for started_note in self.notes_started:
                if started_note[0] == note_id:
                    note_to_end = started_note
                    break
            if note_to_end is not None:
                self.notes_started.remove(note_to_end)
        elif len(self.notes_started) > 0:
            # if no note_id is specified, just end the note that has been going the longest
            note_to_end = self.notes_started.pop(0)

        if note_to_end is None:
            # no appropriate note has been found to end
            return

        note_id, pitch, volume, start_time, variant_dictionary = note_to_end
        # call the specific implementation to stop the note
        self._do_end_note(note_id)
        # record the note in the hosting playcorder, if it's recording
        if start_time is not None and self.host_playcorder.get_time_passed() is not None:
            self.host_playcorder.record_note(self, pitch, volume, self.host_playcorder.get_time_passed()-start_time,
                                             start_time=start_time, variant_dictionary=variant_dictionary)

    def end_all_notes(self):
        while len(self.notes_started) > 0:
            self.end_note()

    def num_notes_playing(self):
        return len(self.notes_started)


class MidiPlaycorderInstrument(PlaycorderInstrument):

    def __init__(self, synth, soundfont_id, bank_and_preset, start_channel, num_channels, host_playcorder=None, name=None):
        assert isinstance(synth, Synth)
        assert isinstance(host_playcorder, Playcorder)
        PlaycorderInstrument.__init__(self, host_playcorder=host_playcorder, name=name)

        self.host_playcorder = host_playcorder
        self.name = name

        self.synth = synth
        self.sound_font_id = soundfont_id

        self.current_channel = 0
        self.start_channel = start_channel
        self.num_channels = num_channels

        # set all the channels owned by this instrument to the correct preset
        # bank_and_preset should be a tuple in the form (bank, preset)
        self.set_to_preset(*bank_and_preset)

    def set_to_preset(self, bank, preset):
        for i in range(self.start_channel, self.start_channel + self.num_channels):
            self.synth.program_select(i, self.sound_font_id, bank, preset)

    def _do_start_note(self, pitch, volume, variant_dictionary=None):
        # Does the actual sonic implementation of starting a note
        # in this case the note_id returned will be a tuple consisting of the channel and the midi key pressed
        channel = self.start_channel + self.current_channel
        self.current_channel = (self.current_channel + 1) % self.num_channels
        int_pitch = int(round(pitch))
        pitch_bend_val = int((pitch - int_pitch)*4096)
        self.synth.pitch_bend(channel, pitch_bend_val)
        self.synth.noteon(channel, int_pitch, int(volume*127))
        return channel, int_pitch

    def _do_end_note(self, note_id):
        # Does the actual sonic implementation of ending a the note with the given note_id = channel, key pressed
        channel, int_pitch = note_id
        self.synth.noteon(channel, int_pitch, 0)

    def _do_play_note(self, pitch, volume, length, start_delay, variant_dictionary):
        # Does the actual sonic implementation of playing a note
        time.sleep(start_delay)
        note_start_time = time.time()
        if hasattr(volume, "__len__") or hasattr(pitch, "__len__"):
            # either volume or pitch or both have an envelope associated, so we start a thread to adjust it
            if hasattr(pitch, "__len__"):
                pitch_curve = MidiPlaycorderInstrument.standardize_parameter_curve(pitch)
                start_pitch = MidiPlaycorderInstrument.get_param_value_at_curve_progress(pitch_curve, 0)
            else:
                pitch_curve = None
                start_pitch = pitch
            if hasattr(volume, "__len__"):
                volume_curve = MidiPlaycorderInstrument.standardize_parameter_curve(volume)
                start_velocity = max(volume_curve[0])
            else:
                volume_curve = None
                start_velocity = volume

            note_id = self._do_start_note(start_pitch, start_velocity, variant_dictionary)

            def animate_pitch_and_volume():
                while note_start_time is not None:
                    if  pitch_curve is not None:
                        self.change_note_pitch(
                            note_id,
                            MidiPlaycorderInstrument.get_param_value_at_curve_progress(
                                pitch_curve, min(1, (time.time() - note_start_time) / length)
                            )
                        )
                    if volume_curve is not None:
                        self.change_note_volume(
                            note_id,
                            MidiPlaycorderInstrument.get_param_value_at_curve_progress(
                                volume_curve, min(1, (time.time() - note_start_time) / length)
                            )
                        )
                    time.sleep(0.04)

            threading.Thread(target=animate_pitch_and_volume).start()
        else:
            note_id = self._do_start_note(pitch, volume, variant_dictionary)

        time.sleep(length)
        note_start_time = None
        self._do_end_note(note_id)

    @staticmethod
    def standardize_parameter_curve(curve_array):
        # a param curve can be given as just a set of values like [1, 0.5, 0.3], which will be evenly spread in time
        # or as [[1, 0.5, 0.3], [0.2, 0.8]], which makes the first segment last 20% of the note length and the last 80%
        # or as [[1, 0.5, 0.3], [0.2, 0.8], [2, 0.5]], which adds a curvature parameter
        # this function standardizes it, taking any of the three forms and returning the latter.
        if hasattr(curve_array[0], "__len__"):
            # we were given levels and percent timings, and possibly curvature values
            if len(curve_array) == 2:
                # given levels and percent timings
                try:
                    assert hasattr(curve_array[1], "__len__") and len(curve_array[1]) == len(curve_array[0]) - 1
                except AssertionError:
                    raise ValueError("There should be exactly one fewer segment length than value")
                total_timings = sum(curve_array[1])
                timings = [float(x) / total_timings for x in curve_array[1]]
                return [curve_array[0], timings, [1] * len(curve_array[1])]
            elif len(curve_array) >= 3:
                try:
                    assert hasattr(curve_array[1], "__len__") and len(curve_array[1]) == len(curve_array[0]) - 1 and \
                           len(curve_array[2]) == len(curve_array[1])
                except AssertionError:
                    raise ValueError("There should be exactly one fewer segment length and curve type than value")
                total_timings = sum(curve_array[1])
                timings = [float(x) / total_timings for x in curve_array[1]]
                return [curve_array[0], timings, curve_array[2]]
        else:
            # just given levels, so we linearly interpolate segments of equal length
            levels = curve_array
            timings = [1.0 / (len(levels) - 1)] * (len(levels) - 1)
            curves = [1.0] * (len(levels) - 1)
            return [levels, timings, curves]

    @staticmethod
    def get_param_value_at_curve_progress(standardized_param_curve, progress):
        values, timings, curves = standardized_param_curve
        for i, segment_length in enumerate(timings):
            if progress > segment_length:
                progress -= segment_length
            else:
                segment_progress = (progress / segment_length) ** curves[i]
                return values[i] * (1 - segment_progress) + values[i+1] * segment_progress


    def change_note_pitch(self, note_id, new_pitch):
        # Changes the pitch of the note started at channel
        channel, int_pitch = note_id
        pitch_bend_val = int((new_pitch - int_pitch) * 4096)
        # unfortunately there is a limit of -8192 to 8192 (or 4 half-steps up or down), so we confine it to this range
        pitch_bend_val = min(max(pitch_bend_val, -8192), 8191)
        self.synth.pitch_bend(channel, pitch_bend_val)

    def change_note_volume(self, note_id, new_volume):
        # Changes the expression of the note with the given id
        channel, int_pitch = note_id
        self.synth.cc(channel, 11, int(new_volume * 127))

# -------------- EXAMPLE --------------
#
# pc = Playcorder(soundfont_path="default")
#
# piano = pc.add_midi_part((0, 0), "Piano")
# guitar = pc.add_midi_part((0, 27), "Guitar")
#
# pc.start_recording([piano, guitar], manual_time=True)
#
# import random
# for i in range(15):
#     l = random.random()*1.5+0.1
#     random.choice([piano, guitar]).play_note(50 + random.random()*20, 0.5, l)
#     pc.wait(l+random.random()*1.5)
#
# pc.stop_recording()
#
# pc.save_to_xml_file(file_name="bob.xml", time_signature="5/4", tempo=120, divisions=6, add_sibelius_pitch_bend=True)