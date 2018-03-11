import threading
import time

from .recording_to_xml import save_to_xml_file as save_recording_to_xml
from .recording_to_xml import separate_into_non_overlapping_voices, quantize_recording
from .measures_beats_notes import *
from midiutil.MidiFile import MIDIFile
from .playcorder_utilities import round_to_multiple, make_flat_list

from .combined_midi_player import CombinedMidiPlayer, register_default_soundfont, unregister_default_soundfont

from.simple_rtmidi_wrapper import get_available_midi_output_devices

from warnings import warn


# TODO: SOMETHING GOES WRONG WHEN THERE ARE LIKE 3 STAVES, and they get disconnected
# TODO: SPECIFY MAX VOICES PER STAFF
# TODO: SPECIFY MOST APPROPRIATE CLEF FOR EACH STAFF OF EACH MEASURE


# TODO: figure out if the pitch bend is not working right in the rt_midi output
# TODO: Test on mac!
# TODO: List ports from Playcorder


class Playcorder:

    def __init__(self, soundfonts=None, audio_driver=None, midi_output_device=None):
        """

        :param soundfonts: the names / paths of the soundfonts this playcorder will use
        :param audio_driver: the driver used to output audio (if none, defaults to whatever fluidsynth chooses)
        :param midi_output_device: the default midi_output_device for outgoing midi streams. These can also be
        specified on a per-instrument basis, but this sets a global default. Defaults to creating virtual devices.
        """

        # list of the current instruments used by this playcorder
        self.instruments = []

        # if we are using just one soundfont no need to put it in a list
        soundfonts = [soundfonts] if isinstance(soundfonts, str) else soundfonts
        self.midi_player = CombinedMidiPlayer(soundfonts, audio_driver, midi_output_device)

        # --- Recording Setup ---
        # parts_being_recorded is a list of parts being recorded if recording otherwise it's None
        self.parts_being_recorded = None
        # once recording stops parts_recorded stores the parts that were recorded
        self.parts_recorded = None
        # recording_start_time is used if using time.time() as time
        # time_passed is used if manually recording time
        self.recording_start_time = None
        self.time_passed = None

    def get_instruments_with_substring(self, word, avoid=None, soundfont_index=0):
        return self.midi_player.get_instruments_with_substring(word, avoid=avoid, soundfont_index=soundfont_index)

    @staticmethod
    def get_available_midi_output_devices():
        return get_available_midi_output_devices()

    @staticmethod
    def register_default_soundfont(name, soundfont_path):
        return register_default_soundfont(name, soundfont_path)

    @staticmethod
    def unregister_default_soundfont(name):
        return unregister_default_soundfont(name)

    def add_part(self, instrument):
        """
        Adds an instance of PlaycorderInstrument to this playcorder. Generally this will be done indirectly
        by calling add_midi_part, but this functionality is here so that people can build and use their own
        PlaycorderInstruments that implement the interface and playback sounds in different ways.
        :type instrument: PlaycorderInstrument
        """
        assert isinstance(instrument, PlaycorderInstrument)
        if not hasattr(instrument, "name") or instrument.name is None:
            instrument.name = "Track " + str(len(self.instruments) + 1)
        instrument.host_playcorder = self
        self.instruments.append(instrument)

    def add_midi_part(self, name=None, preset=(0, 0), soundfont_index=0, num_channels=8,
                      midi_output_device=None, midi_output_name=None):
        """
        Constructs a MidiPlaycorderInstrument, adds it to the Playcorder, and returns it
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

        instrument = MidiPlaycorderInstrument(self, self.midi_player, name, preset, soundfont_index, num_channels,
                                              midi_output_device, midi_output_name)

        self.add_part(instrument)
        return instrument

    def add_silent_part(self, name=None):
        """
        Constructs a basic (and therefore silent) PlaycorderInstrument, adds it to the Playcorder, and returns it
        :rtype : PlaycorderInstrument
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
            instrument.recording.append(PCNote(start_time=note_start_time,
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
        else:
            # if note recording, just default to returning time.time() so that
            # relative measurements that use this will still work
            return time.time()

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
                    assert isinstance(pc_note, PCNote)
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
        called a MidiPlaycorderInstrument, uses fluidsynth to playback sounds from a soundfont, and also sends the
        output to a port via rtmidi. Other implementations could playback sounds in a different way.
        :param host_playcorder: The playcorder that this instrument acts within
        :param name: The name of this instrument (used later in labeling parts in output)
        """
        assert isinstance(host_playcorder, Playcorder)
        self.host_playcorder = host_playcorder
        self.name = name
        self.notes_started = []   # each entry goes (note_id, pitch, volume, start_time, variant_dictionary)

    # ------------------ Methods to be implemented by subclasses ------------------

    def _do_play_note(self, pitch, volume, length, start_delay, variant_dictionary=None):
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
        # returns the note_id as a reference, in case we want to change pitch mid-playback
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

    def __init__(self, host_playcorder, midi_player, name, preset, soundfont_index=0, num_channels=8,
                 midi_output_device=None, midi_output_name=None):
        assert isinstance(host_playcorder, Playcorder)
        assert isinstance(midi_player, CombinedMidiPlayer)
        super().__init__(host_playcorder, name)

        self.midi_player = midi_player
        midi_output_name = name if midi_output_name is None else midi_output_name
        self.midi_instrument = midi_player.add_instrument(num_channels, preset, soundfont_index,
                                                          midi_output_device, midi_output_name)
        self.num_channels = num_channels

        # keep track of what notes are currently playing
        # each entry is an identifying tuple of: (channel, pitch, unique_id)
        self.active_midi_notes = []

    # ---- highest level call to implement playing a note ----
    # started as a thread from within the parent class method play_note

    def _do_play_note(self, pitch, volume, length, start_delay, variant_dictionary=None):
        # Does the actual sonic implementation of playing a note
        time.sleep(start_delay)
        note_start_time = time.time()
        # convert lists to ParameterCurves
        volume = ParameterCurve.from_list(volume) if hasattr(volume, "__len__") else volume
        pitch = ParameterCurve.from_list(pitch) if hasattr(pitch, "__len__") else pitch
        is_animating_volume = isinstance(volume, ParameterCurve)
        is_animating_pitch = isinstance(pitch, ParameterCurve)
        # the starting volume (velocity) of the note needs to be as loud as the note is ever going to get
        start_volume = volume.max_value() if isinstance(volume, ParameterCurve) else volume
        # the starting pitch should just be whatever it is
        start_pitch = pitch.value_at(0) if isinstance(pitch, ParameterCurve) else pitch

        note_id = self._do_start_note(start_pitch, start_volume, variant_dictionary,
                                      pitch_changes=is_animating_pitch)

        if is_animating_volume or is_animating_pitch:
            if is_animating_volume:
                volume.normalize_to_duration(length)
            if is_animating_pitch:
                pitch.normalize_to_duration(length)

            def animate_pitch_and_volume():
                while note_start_time is not None:
                    if is_animating_volume:
                        # note that, since change_note_volume is affecting expression values, we need to send it
                        # the proportion of the start_volume rather than the absolute volume
                        self.change_note_volume(note_id, volume.value_at(time.time() - note_start_time) / start_volume)
                    if is_animating_pitch:
                        self.change_note_pitch(note_id, pitch.value_at(time.time() - note_start_time))
                    time.sleep(0.04)
            threading.Thread(target=animate_pitch_and_volume).start()

        time.sleep(length)
        note_start_time = None
        self._do_end_note(note_id)

    # ---- The constituent parts of the _do_play_note call ----

    def _do_start_note(self, pitch, volume, variant_dictionary=None, pitch_changes=False):
        # Does the actual sonic implementation of starting a note
        # in this case the note_id returned will be a tuple consisting of
        # the channel, the midi key pressed, the start time, and whether or not pitch bend is used
        int_pitch = int(round(pitch))
        uses_pitch_bend = (pitch != int_pitch) or pitch_changes
        channel = self._find_channel_for_note(int_pitch, new_note_uses_bend=uses_pitch_bend)
        self.midi_instrument.pitch_bend(channel, pitch - int_pitch)
        self.midi_instrument.note_on(channel, int_pitch, volume)
        note_id = channel, int_pitch, self.host_playcorder.get_time_passed(), uses_pitch_bend
        self.active_midi_notes.append(note_id)
        return note_id

    def _find_channel_for_note(self, int_pitch, new_note_uses_bend=False):
        # returns the first channel not currently playing this pitch
        # this could undoubtedly be more efficient, but it's probably not worth the effort
        available_channels = list(range(self.num_channels))
        old_notes_that_conflict = []  # we keep track of these to end them in case there is no free channel
        for active_midi_note in self.active_midi_notes:
            chan, pitch, start_time, uses_bend = active_midi_note
            # for each active midi note, check if it's playing this pitch and thus would conflict on the same channel
            # also, if the new note uses pitch bend, or if the old note we're checking it against does, then they
            # can't share a channel, since the pitch bend applies to the whole channel.
            if pitch == int_pitch or new_note_uses_bend or uses_bend:
                # if so, mark the channel that note is on as unavailable
                if chan in available_channels:
                    available_channels.remove(chan)
                old_notes_that_conflict.append(active_midi_note)
        if len(available_channels) > 0:
            # if there's a free channel, return the lowest number available
            return available_channels[0]
        else:
            # if every channel is playing this pitch, we will end the oldest note so we can
            old_notes_that_conflict.sort(key=lambda note_info: note_info[2])
            oldest_note = old_notes_that_conflict[0]
            self._do_end_note(oldest_note)
            # return the channel of the oldest note
            return oldest_note[0]

    def _do_end_note(self, note_id):
        # Does the actual sonic implementation of ending a the note with the given note_id = channel, key pressed
        if note_id in self.active_midi_notes:
            self.midi_instrument.note_off(note_id[0], note_id[1])
            self.active_midi_notes.remove(note_id)

    def change_note_pitch(self, note_id, new_pitch):
        # Changes the pitch of the note started at channel
        channel, int_pitch, note_start_time, uses_pitch_bend = note_id
        self.midi_instrument.pitch_bend(channel, new_pitch - int_pitch)

    def change_note_volume(self, note_id, new_volume):
        """
        Changes the volume of the note with the given id
        For a MidiPlaycorderInstrument, this is mapped to expression, which means that new_volume represents a
        proportion of the starting volume of the note. The note can't get louder than it started.
        """
        channel, int_pitch, note_start_time, uses_pitch_bend = note_id
        self.midi_instrument.expression(channel, new_volume)

    def set_max_pitch_bend(self, semitones):
        self.midi_instrument.set_max_pitch_bend(semitones)


class ParameterCurve:

    def __init__(self, levels, durations, curvatures):
        if len(levels) == len(durations):
            # there really should be one more level than duration, but if there's the same
            # number, we assume that they intend the last level to stay where it is
            levels = list(levels) + [levels[-1]]
        if len(levels) != len(durations) + 1:
            raise ValueError("Inconsistent number of levels and durations given.")
        if len(curvatures) > len(levels) - 1:
            warn("Too many curvature values given to ParameterCurve. Discarding extra.")
        if len(curvatures) < len(levels) - 1:
            warn("Too few curvature values given to ParameterCurve. Assuming linear for remainder.")

        self.levels = levels
        self.durations = durations
        self.curvatures = curvatures

    @classmethod
    def from_levels(cls, levels):
        # just given levels, so we linearly interpolate segments of equal length
        durations = [1.0 / (len(levels) - 1)] * (len(levels) - 1)
        curves = [1.0] * (len(levels) - 1)
        return cls(levels, durations, curves)

    @classmethod
    def from_levels_and_durations(cls, levels, durations):
        # given levels and durations, so we assume linear curvature for every segment
        return cls(levels, durations, [1.0] * (len(levels) - 1))

    @classmethod
    def from_list(cls, constructor_list):
        # converts from a list that may contain just levels, may have levels and durations, and may have everything
        # a input of [1, 0.5, 0.3] is interpreted as evenly spaced levels
        # an input of [[1, 0.5, 0.3], [0.2, 0.8]] is interpreted as levels and durations
        # an input of [[1, 0.5, 0.3], [0.2, 0.8], [2, 0.5]]is interpreted as levels, durations, and curvatures
        if hasattr(constructor_list[0], "__len__"):
            # we were given levels and durations, and possibly curvature values
            if len(constructor_list) == 2:
                # given levels and durations
                return ParameterCurve.from_levels_and_durations(constructor_list[0], constructor_list[1])
            elif len(constructor_list) >= 3:
                # given levels, durations, and curvature values
                return cls(constructor_list[0], constructor_list[1], constructor_list[2])
        else:
            # just given levels
            return ParameterCurve.from_levels(constructor_list)

    def normalize_to_duration(self, desired_duration):
        current_duration = sum(self.durations)
        if current_duration != desired_duration:
            ratio = desired_duration / current_duration
            for i, dur in enumerate(self.durations):
                self.durations[i] = dur * ratio

    def value_at(self, t):
        if t < 0:
            return self.levels[-1]
        for i, segment_length in enumerate(self.durations):
            if t > segment_length:
                t -= segment_length
            else:
                segment_progress = (t / segment_length) ** self.curvatures[i]
                return self.levels[i] * (1 - segment_progress) + self.levels[i+1] * segment_progress
        return self.levels[-1]

    def max_value(self):
        return max(self.levels)

    def __repr__(self):
        return "ParameterCurve({}, {}, {})".format(self.levels, self.durations, self.curvatures)


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