import itertools
from .spelling import SpellingPolicy
from .note_properties import NotePropertiesDictionary
from .playback_implementations import *
from scamp.utilities import iterate_all_subclasses
from clockblocks import *
import logging
import time
from typing import Union, Sequence, List
from numbers import Number
from threading import Lock


class NoteHandle:

    def __init__(self, note_id, instrument):
        self.note_id = note_id
        self.instrument: ScampInstrument = instrument

    def change_parameter(self, param_name, target_value_or_values: Union[Sequence, Number],
                         transition_length_or_lengths: Union[Sequence, Number] = 0,
                         transition_curve_shape_or_shapes: Union[Sequence, Number] = 0, clock="auto"):
        self.instrument.change_note_parameter(self.note_id, param_name, target_value_or_values,
                                              transition_length_or_lengths, transition_curve_shape_or_shapes, clock)

    def change_pitch(self, target_value_or_values: Union[Sequence, Number],
                     transition_length_or_lengths: Union[Sequence, Number] = 0,
                     transition_curve_shape_or_shapes: Union[Sequence, Number] = 0, clock="auto"):
        self.instrument.change_note_pitch(self.note_id, target_value_or_values, transition_length_or_lengths,
                                          transition_curve_shape_or_shapes, clock)

    def change_volume(self, target_value_or_values: Union[Sequence, Number],
                      transition_length_or_lengths: Union[Sequence, Number] = 0,
                      transition_curve_shape_or_shapes: Union[Sequence, Number] = 0, clock="auto"):
        self.instrument.change_note_volume(self.note_id, target_value_or_values, transition_length_or_lengths,
                                           transition_curve_shape_or_shapes, clock)

    def split(self, clock="auto"):
        self.instrument.split_note(self.note_id, clock)

    def end(self):
        self.instrument.end_note(self.note_id)

    def __repr__(self):
        return "NoteHandle({}, {})".format(self.note_id, self.instrument)


class ChordHandle:

    def __init__(self, note_handles: Sequence[NoteHandle], intervals: Sequence[Number]):
        self.note_handles = tuple(note_handles) if not isinstance(note_handles, tuple) else note_handles
        self.intervals = tuple(intervals) if not isinstance(intervals, tuple) else intervals

    def change_parameter(self, param_name, target_value_or_values: Union[Sequence, Number],
                         transition_length_or_lengths: Union[Sequence, Number] = 0,
                         transition_curve_shape_or_shapes: Union[Sequence, Number] = 0, clock="auto"):
        for note_handle in self.note_handles:
            note_handle.change_parameter(param_name, target_value_or_values, transition_length_or_lengths,
                                         transition_curve_shape_or_shapes, clock)

    def change_pitch(self, target_value_or_values: Union[Sequence, Number],
                     transition_length_or_lengths: Union[Sequence, Number] = 0,
                     transition_curve_shape_or_shapes: Union[Sequence, Number] = 0, clock="auto"):
        for note_handle, interval in zip(self.note_handles, self.intervals):
            this_note_pitch_targets = [target_value + interval for target_value in target_value_or_values] \
                if hasattr(target_value_or_values, "__len__") else target_value_or_values + interval
            note_handle.change_pitch(this_note_pitch_targets, transition_length_or_lengths,
                                     transition_curve_shape_or_shapes, clock)

    def change_volume(self, target_value_or_values: Union[Sequence, Number],
                      transition_length_or_lengths: Union[Sequence, Number] = 0,
                      transition_curve_shape_or_shapes: Union[Sequence, Number] = 0, clock="auto"):
        for note_handle in self.note_handles:
            note_handle.change_volume(target_value_or_values, transition_length_or_lengths,
                                      transition_curve_shape_or_shapes, clock)

    def split(self, clock="auto"):
        for note_handle in self.note_handles:
            note_handle.split(clock)

    def end(self):
        for note_handle in self.note_handles:
            note_handle.end()


class ParameterChangeSegment(EnvelopeSegment):

    def __init__(self, parameter_change_function, start_value, target_value, transition_length, transition_curve_shape,
                 clock, call_priority, temporal_resolution=0.01):
        """
        Convenient class for handling interruptable transitions of parameter values and storing info on them
        :param parameter_change_function: since this is for general parameters, we pass the function to be called
        to set the parameter. Generally will call _do_change_note_parameter/pitch/volume for a given note_id
        :param start_value: start value of the parameter in the transition
        :param target_value: target value of the parameter in the transition
        :param transition_length: length of the transition in beats on the clock given
        :param transition_curve_shape: curve shape of the transition
        :param clock: the clock that all of this happens in reference to
        :param call_priority: this is used to determine which call to change_parameter happened first, since once these
        things get spawned in threads, the order gets indeterminate.
        :param temporal_resolution: time resolution of the unsynchronized process. One of the following:
         - just a number (in seconds)
         - the string "pitch-based", in which case we derive it based on trying to get a smooth pitch change
         - the string "volume-based", in which case we derive it based on trying to get a smooth volume change.
        """
        # set this up as an envelope
        super().__init__(0, transition_length, start_value, target_value, transition_curve_shape)
        # "do_change_parameter" feels more like an action name
        self.do_change_parameter = parameter_change_function

        self.clock = clock  # the parent clock that this process runs on
        self._run_clock = None  # the sub-clock created by forking this process
        self.running = False  # flag used for aborting the unsynchronized process

        # some of the key data that this envelope holds onto are the time stamps at which it starts and finishes
        # this can be used to construct the appropriate envelope segment on whichever clock we're recording on
        self.start_time_stamp = None
        self.end_time_stamp = None
        self.call_priority = call_priority

        self.temporal_resolution = temporal_resolution

    def run(self, silent=False):
        """
        Runs the segment from start to finish, gradually changing the parameter.
        This function runs as a synchronized clock process (it should be forked), and it starts a parallel,
        unsynchronized process ("_animation_function") to do the actual calls to change parameter
        :param silent: this flag causes none of the animation to actually happen. This is used when we're trying to
        notate a note but not play it back, as in the case of a note that has been adjusted (where we playback -- but
        don't notate -- the adjusted version, while we run -- but don't play back -- the unadjusted version.)
        """
        self.start_time_stamp = TimeStamp(self.clock)

        # if this segment has no duration, no need to do any animation
        # just set it to the final value and return
        if self.duration == 0:
            self.end_time_stamp = TimeStamp(self.clock)
            self.do_change_parameter(self.end_level)
            return

        self.start_time_stamp = TimeStamp(self.clock)
        self.running = True  # used to kill the unsynchronized process when we abort or this synchronized one ends

        # we note down the clock we're running this on. If abort is called, this clock gets killed
        self._run_clock = current_clock()

        # if there's no change, or if we're skipping animation, just wait and finish
        if self.end_level == self.start_level or silent:
            wait(self.duration)
            self.end_time_stamp = TimeStamp(self.clock)
            self.do_change_parameter(self.end_level)
            self.running = False
            return

        # determine the time increment, perhaps by calculating a good one for the given parameter
        if self.temporal_resolution == "pitch-based":
            time_increment = self._get_good_pitch_bend_temporal_resolution()
        elif self.temporal_resolution == "volume-based":
            time_increment = self._get_good_volume_temporal_resolution()
        else:
            time_increment = self.temporal_resolution
        # don't animate faster than 4ms though
        time_increment = max(0.004, time_increment)

        def _animation_function():
            # does the intermediate changing of values; since it's sleeping in small time increments, we fork it
            # as unsynchronized parallel process so that it doesn't gum up the clocks with the overhead of
            # waking and sleeping rapidly
            beats_passed = 0

            while beats_passed < self.duration and self.running:
                start = time.time()
                if beats_passed > 0:  # no need to change the parameter the first time, before we had a chance to wait
                    self.do_change_parameter(self.value_at(beats_passed))
                time.sleep(time_increment)
                # TODO: Absolute_rate would be great, except that it doesn't update between synchronized clock events
                # Is there a way of improving this??
                beats_passed += (time.time() - start) * self.clock.absolute_rate()

        # start the unsynchronized animation function
        self.clock.fork_unsynchronized(_animation_function)
        # waits in a synchronized fashion so that it can save an accurate time stamp at the end
        wait(self.duration)

        # we only get here if it wasn't aborted while running, since that will call kill on the child clock
        self.running = False
        self.end_time_stamp = TimeStamp(self.clock)
        self.do_change_parameter(self.end_level)

    def abort_if_running(self):
        if self.running:
            # if we were running, we save the time stamp at which we aborted as the end time stamp
            self.end_time_stamp = TimeStamp(self.clock)
            self._run_clock.kill()  # kill the clock doing the "run" function
            # since the units of this envelope are beats in self.clock, se how far we got in the envelope by
            # subtracting converting the start and end time stamps to those beats and subtracting
            how_far_we_got = self.end_time_stamp.beat_in_clock(self.clock) - \
                             self.start_time_stamp.beat_in_clock(self.clock)

            # now split there, discarding the rest of the envelope. This makes self.end_level the value we ended up at.
            if self.start_time < how_far_we_got < self.end_time:
                self.split_at(how_far_we_got)
            elif self.start_time == how_far_we_got:
                # this was aborted before it even got going. Later, the transcriber will ignore this nothing segment
                self.end_time = self.start_time
                self.end_level = self.start_level
                self.running = False
                return

            self.do_change_parameter(self.end_level)  # set it to where we should be at this point
        self.running = False  # this will make sure to abort the animation function

    def completed(self):
        # it's not running, but because it finished, not because it never started
        return not self.running and self.end_time_stamp is not None

    def _get_good_pitch_bend_temporal_resolution(self):
        """
        Returns a reasonable temporal resolution, based on this clock's envelope and rate, assuming it's a pitch curve
        """
        max_cents_per_second = self.max_absolute_slope() * 100 * self.clock.absolute_rate()
        # cents / update * updates / sec = cents / sec   =>  updates_freq = cents_per_second / cents_per_update
        # we'll aim for 4 cents per update, since some say the JND is 5-6 cents
        update_freq = max_cents_per_second / 4.0
        return 1 / update_freq

    def _get_good_volume_temporal_resolution(self):
        """
        Returns a reasonable temporal resolution, based on this clock's envelope and rate, assuming it's a volume curve
        """
        max_volume_per_second = self.max_absolute_slope() * self.clock.absolute_rate()
        # based on the idea that for midi volumes, it's quantized from 0 to 127, so there's not much point in updating
        # in between those quantization levels. It's a decent enough rule even if not using midi output.
        update_freq = max_volume_per_second * 127
        return 1 / update_freq

    def __repr__(self):
        return "ParameterChangeSegment[{}, {}, {}, {}, {}]".format(
            self.start_time_stamp, self.end_time_stamp, self.start_level, self.end_level, self.curve_shape
        )


class ScampInstrument(SavesToJSON):

    _note_id_generator = itertools.count()
    _change_param_call_counter = itertools.count()

    def __init__(self, name=None, ensemble=None):
        """
        Base instrument class.
        """
        self.name = name
        # used to help distinguish between identically named instruments in the same ensemble
        self.name_count = ensemble.get_part_name_count(self.name) if ensemble is not None else 0

        self.ensemble = ensemble
        self._transcribers_to_notify = []

        self._note_info_by_id = {}
        self.playback_implementations: List[PlaybackImplementation] = []

        # A policy for spelling notes used as the default for this instrument. Overrides any broader defaults.
        # (Has a getter and setter method allowing constructor strings to be passed.)
        self._default_spelling_policy = None

        super().__init__()

    def play_chord(self, pitches, volume, length, properties=None, blocking=True, clock="auto"):
        """
        Simple utility for playing chords without having to play notes with blocking=False
        Takes a list of pitches, and passes them to play_note
        """
        assert hasattr(pitches, "__len__")

        properties = self._standardize_properties(properties)

        # we should either be given a number of noteheads equal to the number of pitches or just one notehead for all
        assert len(properties.noteheads) == len(pitches) or len(properties.noteheads) == 1, \
            "Wrong number of noteheads for chord."

        for i, pitch in enumerate(pitches[:-1]):
            # for all but the last pitch, play it without blocking, so we can start all the others
            # also copy the properties dictionary, and pick out the correct notehead if we've been given several
            properties_copy = deepcopy(properties)
            if len(properties.noteheads) > 1:
                properties_copy.noteheads = [properties_copy.noteheads[i]]
            self.play_note(pitch, volume, length, properties=properties_copy, blocking=False, clock=clock)

        # for the last pitch, block or not based on the blocking parameter
        # also, if we've been given a list of noteheads, pick out the last one
        if len(properties.noteheads) > 1:
            properties.noteheads = [properties.noteheads[-1]]
        self.play_note(pitches[-1], volume, length, properties=properties, blocking=blocking, clock=clock)

    def play_note(self, pitch, volume, length, properties=None, blocking=True, clock="auto"):
        """
        Play a note on this instrument, using the given clock
        :param pitch: either a number, an Envelope, or a list used to create an Envelope
        :param volume: either a number, an Envelope, or a list used to create an Envelope
        :param length: either a number (of beats), or a tuple representing a set of tied segments
        :param properties: either a string, list, dictionary or NotePropertiesDictionary representing note properties
        :param blocking: if true, don't return until the note is done playing; if false, return immediately
        :param clock: which clock to use. If "auto", capture the clock from context.
        """
        clock = ScampInstrument._resolve_clock_argument(clock)

        properties = self._standardize_properties(properties)
        pitch = Envelope.from_list(pitch) if hasattr(pitch, "__len__") else pitch
        volume = Envelope.from_list(volume) if hasattr(volume, "__len__") else volume

        adjusted_pitch, adjusted_volume, adjusted_length, did_an_adjustment = \
            properties.apply_playback_adjustments(pitch, volume, length)

        if did_an_adjustment:
            adjusted_pitch = Envelope.from_list(adjusted_pitch) \
                if hasattr(adjusted_pitch, "__len__") else adjusted_pitch
            adjusted_volume = Envelope.from_list(adjusted_volume) \
                if hasattr(adjusted_volume, "__len__") else adjusted_volume
            # play, but don't transcribe the modified version (though only if the clock is not fast-forwarding)
            if not clock.is_fast_forwarding():
                clock.fork(self._do_play_note,
                           extra_args=(adjusted_pitch, adjusted_volume, adjusted_length, properties),
                           kwargs={"transcribe": False})
            # transcribe, but don't play the unmodified version
            if blocking:
                self._do_play_note(clock, pitch, volume, length, properties, silent=True)
            else:
                clock.fork(self._do_play_note, name="DO_PLAY_NOTE",
                           extra_args=(pitch, volume, length, properties), kwargs={"silent": True})
        else:
            # No adjustments, so no need to separate transcription from playback
            # (However, if the clock is fast-forwarding, make it silent)
            if blocking:
                self._do_play_note(clock, pitch, volume, length, properties, silent=clock.is_fast_forwarding())
            else:
                clock.fork(self._do_play_note, name="DO_PLAY_NOTE",
                           extra_args=(pitch, volume, length, properties),
                           kwargs={"silent": clock.is_fast_forwarding()})

    def _do_play_note(self, clock, pitch, volume, length, properties, silent=False, transcribe=True):
        """
        This runs the actual thread that plays the note, and is scheduled when play_note is called.
        If playback adjustments were made, then we schedule the altered version of _do_play_note to play back, but with
        "transcribe" set to false, and we schedule an unaltered version of _do_play_note to run silently, but with
        "transcribe" set to true. This way the transcription is not affected by performance adjustments.
        :param clock: which clock this plays back on
        :param pitch: either a number, an Envelope
        :param volume: either a number, an Envelope
        :param length: either a number (of beats), or a tuple representing a set of tied segments
        :param properties: a NotePropertiesDictionary
        :param silent: if True, don't actually do any of the playback; just go through the motions for transcribing it
        :param transcribe: if False, don't notify Transcribers at the end of the note
        """
        # length can either be a single number of beats or a list/tuple or segments to be split
        # sum_length will represent the total number of beats in either case
        sum_length = sum(length) if hasattr(length, "__len__") else length

        # normalize all envelopes to to the duration of the note
        if isinstance(pitch, Envelope):
            pitch.normalize_to_duration(sum_length)
        if isinstance(volume, Envelope):
            volume.normalize_to_duration(sum_length)
        for param, value in properties.iterate_extra_parameters_and_values():
            if isinstance(value, Envelope):
                value.normalize_to_duration(sum_length)

        # if we know ahead of time that neither pitch nor volume changes, we can pass
        fixed = not isinstance(pitch, Envelope) and not isinstance(volume, Envelope)

        # start the note. (Note that this will also start the animation of pitch, volume,
        # and any other parameters if they are envelopes.)
        note_handle = self.start_note(
            pitch, volume, properties, clock=clock, silent=silent, transcribe=transcribe, fixed=fixed,
            max_volume=volume.max_level() if isinstance(volume, Envelope) else volume)

        if hasattr(length, "__len__"):
            for length_segment in length:
                clock.wait(length_segment)
                note_handle.split(clock)
        else:
            clock.wait(length)
        note_handle.end()

    def start_note(self, pitch, volume, properties=None, clock="auto", silent=False,
                   transcribe=True, fixed=False, max_volume=1):
        """
        Start a note with the given pitch, volume, and properties
        :param pitch: the pitch / starting pitch of the note (not an Envelope)
        :param volume: the volume / starting volume of the note (not an Envelope)
        :param properties: either a string, list, dictionary or NotePropertiesDictionary representing note properties
        :param clock: the clock to run any animation of pitch, volume, etc. on, if applicable
        :param silent: if True, go through the motions of playing back, but don't make sound. Useful if we're trying to
        notate a note but not actually play it. For instance, i.e. when there is some sort of playback alteration like
        staccato, a "silent" note with the original properties that does none of the alterations gets notated,
        while the sounding note gets flagged as transcribe=False.
        :param transcribe: if False, don't notify transcribers of this note when it ends
        :param fixed: if True, disables the ability of this note to change pitch or volume; useful for conserving
        midi_channels, since multiple fixed notes can occupy the same channel.
        :return: a NoteHandle with which to later manipulate the note
        :param max_volume: This is a bit of a pain, but since midi playback requires us to set the velocity at the
        beginning of the note, and thereafter vary volume using expression, and since expression can only make the
        note quieter, we need to start the note with velocity equal to the max desired volume (using expression to
        adjust it down to the actual start volume). The default will be 1, meaning as loud as possible, since unless we
        know in advance what the note is going to do, we need to be prepared to go up to full volume. Using play_note,
        we do actually know in advance how loud the note is going to get, so we can set max volume to the peak of the
        Envelope. Honestly, I wish I could separate this implementation detail from the ScampInstrument class, but I
        don't see how this would be possible.
        """
        clock = ScampInstrument._resolve_clock_argument(clock)

        # standardize properties if necessary, turn pitch and volume into lists if necessary
        properties = self._standardize_properties(properties)
        pitch = Envelope.from_list(pitch) if hasattr(pitch, "__len__") else pitch
        volume = Envelope.from_list(volume) if hasattr(volume, "__len__") else volume

        # get the starting values for all the parameters to pass to the playback implementations
        start_pitch = pitch.start_level() if isinstance(pitch, Envelope) else pitch
        start_volume = volume.start_level() if isinstance(volume, Envelope) else volume
        other_param_start_values = {param: value.start_level() if isinstance(value, Envelope) else value
                                    for param, value in properties.iterate_extra_parameters_and_values()}

        # generate a new id for this note, and set up all of its info
        note_id = next(ScampInstrument._note_id_generator)
        self._note_info_by_id[note_id] = {
            "start_time": TimeStamp(clock),
            "end_time": None,
            "split_points": [],
            "parameter_start_values": dict(other_param_start_values, pitch=start_pitch, volume=start_volume),
            "parameter_values": dict(other_param_start_values, pitch=start_pitch, volume=start_volume),
            "parameter_change_segments": {},
            "segments_list_lock": Lock(),
            "properties": properties,
            "max_volume": max_volume,
            "flags": []
        }

        if fixed:
            assert not isinstance(pitch, Envelope) and not isinstance(volume, Envelope), \
                "The 'fixed' flag can only be used on notes that do not animate pitch or volume."
            self._note_info_by_id[note_id]["flags"].append("fixed")

        if silent:
            # if it's silent, add a flag so that none of the playback implementation happens for the rest of the note
            self._note_info_by_id[note_id]["flags"].append("silent")
        else:
            # otherwise, call all the playback implementation!
            for playback_implementation in self.playback_implementations:
                playback_implementation.start_note(note_id, start_pitch, start_volume,
                                                   properties, other_param_start_values)

        # if we don't want to transcribe it, set that flag
        if not transcribe:
            self._note_info_by_id[note_id]["flags"].append("no_transcribe")

        # create a handle for this note
        handle = NoteHandle(note_id, self)

        # start all the note animation for pitch, volume, and any extra parameters
        # note that, if the note is silent, then start_note has added the silent flag to the note_info dict
        # this will cause unsynchronized animation threads not to fire
        if isinstance(pitch, Envelope):
            handle.change_pitch(pitch.levels[1:], pitch.durations, pitch.curve_shapes, clock)
        if isinstance(volume, Envelope):
            handle.change_volume(volume.levels[1:], volume.durations, volume.curve_shapes, clock)
        for param, value in properties.iterate_extra_parameters_and_values():
            if isinstance(value, Envelope):
                handle.change_parameter(param, value.levels[1:], value.durations, value.curve_shapes, clock)

        return handle

    def start_chord(self, pitches, volume, properties=None, clock="auto", silent=False,
                    transcribe=True, fixed=False, max_volume=1):
        """
        Simple utility for starting chords without having to start each note individually.
        Simply supply a list of pitches.
        Returns a ChordHandle, which is used to manipulate the chord thereafter
        """
        assert hasattr(pitches, "__len__")

        properties = self._standardize_properties(properties)

        # we should either be given a number of noteheads equal to the number of pitches or just one notehead for all
        assert len(properties.noteheads) == len(pitches) or len(properties.noteheads) == 1, \
            "Wrong number of noteheads for chord."

        note_handles = []

        pitches = [Envelope.from_list(pitch) if hasattr(pitch, "__len__") else pitch for pitch in pitches]

        first_pitch_start_level = pitches[0].start_level() if isinstance(pitches[0], Envelope) else pitches[0]
        intervals = [(pitch.start_level() if isinstance(pitch, Envelope) else pitch) - first_pitch_start_level
                     for pitch in pitches]

        for i, pitch in enumerate(pitches):
            # for all but the last pitch, play it without blocking, so we can start all the others
            # also copy the properties dictionary, and pick out the correct notehead if we've been given several
            properties_copy = deepcopy(properties)
            if len(properties.noteheads) > 1:
                properties_copy.noteheads = [properties_copy.noteheads[i]]
            note_handles.append(self.start_note(pitch, volume, properties=properties_copy, clock=clock, silent=silent,
                                                transcribe=transcribe, fixed=fixed, max_volume=max_volume))

        return ChordHandle(note_handles, intervals)

    def _standardize_properties(self, raw_properties) -> NotePropertiesDictionary:
        """
        Turns the properties given into the standard form of a NotePropertiesDictionary
        :param raw_properties: can be None, a string, a list, or a dict
        :return: a NotePropertiesDictionary
        """
        if isinstance(raw_properties, NotePropertiesDictionary):
            return raw_properties

        properties = NotePropertiesDictionary.from_unknown_format(raw_properties) \
            if not isinstance(raw_properties, NotePropertiesDictionary) else raw_properties

        # resolve the spelling policy based on defaults (local first, then more global)
        if properties["spelling_policy"] is None:
            # if the note doesn't say how to be spelled, check the instrument
            if self.default_spelling_policy is not None:
                properties.spelling_policy = self.default_spelling_policy
            # if the instrument doesn't have a default spelling policy check the host (probably a Session)
            elif self.ensemble is not None and self.ensemble.default_spelling_policy is not None:
                properties.spelling_policy = self.default_spelling_policy
            # if the host doesn't have a default, then don't do anything and it will fall back to playback_settings
        return properties

    def change_note_parameter(self, note_id, param_name, target_value_or_values: Union[Sequence, Number],
                              transition_length_or_lengths: Union[Sequence, Number] = 0,
                              transition_curve_shape_or_shapes: Union[Sequence, Number] = 0, clock="auto"):
        """
        Changes the value of parameter of note playback over a given time; can also take a sequence of targets and times
        :param note_id: which note to affect
        :param param_name: name of the parameter to affect. "pitch" and "volume" are special cases
        :param target_value_or_values: target value (or list thereof) for the parameter
        :param transition_length_or_lengths: transition time(s) in beats to the target value(s)
        :param transition_curve_shape_or_shapes: curve shape(s) for the transition(s)
        :param clock: which clock all of this happens on, "auto" captures the clock from context
        """
        clock = ScampInstrument._resolve_clock_argument(clock)

        note_id = note_id.note_id if isinstance(note_id, NoteHandle) else note_id
        note_info = self._note_info_by_id[note_id]

        if "fixed" in note_info["flags"] and param_name in ("pitch", "volume"):
            raise Exception("Cannot change pitch or volume of a note with 'fixed' set to True.")

        # which function do we use to actually carry out the change of parameter? Pitch and volume are special.
        if "silent" in note_info["flags"]:
            # if it's silent, then we don't actually call any of the implementation, so pass a dummy function
            def parameter_change_function(value): note_info["parameter_values"][param_name] = value
            temporal_resolution = None
        elif param_name == "pitch":
            def parameter_change_function(value):
                for playback_implementation in self.playback_implementations:
                    playback_implementation.change_note_pitch(note_id, value)
                note_info["parameter_values"][param_name] = value
            temporal_resolution = "pitch-based"
        elif param_name == "volume":
            def parameter_change_function(value):
                for playback_implementation in self.playback_implementations:
                    playback_implementation.change_note_volume(note_id, value)
                note_info["parameter_values"][param_name] = value
            temporal_resolution = "volume-based"
        else:
            def parameter_change_function(value):
                for playback_implementation in self.playback_implementations:
                    playback_implementation.change_note_parameter(note_id, param_name, value)
                note_info["parameter_values"][param_name] = value
            temporal_resolution = 0.01

        assert param_name in note_info["parameter_values"], \
            "Cannot change parameter {}, as it was undefined at note start.".format(param_name)

        if param_name in note_info["parameter_change_segments"]:
            segments_list = note_info["parameter_change_segments"][param_name]
        else:
            segments_list = note_info["parameter_change_segments"][param_name] = []

        # if there was a previous segment changing this same parameter, and it's not done yet, we should abort it
        if len(segments_list) > 0:
            segments_list[-1].abort_if_running()

        # this helps to keep track of which call to change_note_parameter happened first, since when
        # do_animation_sequence gets forked, order can become indeterminate (see comment there)
        call_priority = next(ScampInstrument._change_param_call_counter)

        if hasattr(target_value_or_values, "__len__"):
            # assume linear segments unless otherwise specified
            transition_curve_shape_or_shapes = [0] * len(target_value_or_values) if \
                transition_curve_shape_or_shapes == 0 else transition_curve_shape_or_shapes
            assert hasattr(transition_length_or_lengths, "__len__") and \
                   hasattr(transition_curve_shape_or_shapes, "__len__")
            assert len(target_value_or_values) == len(transition_length_or_lengths) == \
                   len(transition_curve_shape_or_shapes), \
                "The list of target values must be accompanied by a equal length list of transition lengths and shapes."

            def do_animation_sequence():
                for target, length, shape in zip(target_value_or_values, transition_length_or_lengths,
                                                 transition_curve_shape_or_shapes):
                    with note_info["segments_list_lock"]:
                        if len(segments_list) > 0 and segments_list[-1].running:
                            # if two segments are started at the exact same (clock) time, then we want to abort the one
                            # that was called first. Often that will happen in the call to segments_list[-1].abort_if_
                            # running() above. However, it may be that they both make it through that check before
                            # either is added to the segments list. This checks in on that case, and aborts whichever
                            # segment came from the earlier call to change_note_parameter
                            if call_priority > segments_list[-1].call_priority:
                                # this call to change_note_parameter happened after, abort the other one
                                segments_list[-1].abort_if_running()
                            else:
                                # this call to change_note_parameter happened before, abort
                                return

                        this_segment = ParameterChangeSegment(
                            parameter_change_function, note_info["parameter_values"][param_name], target,
                            length, shape, clock, call_priority, temporal_resolution=temporal_resolution)

                        segments_list.append(this_segment)
                    # note that these segments are not forked individually: they are chained together and called
                    # directly on a function (do_animation_sequence) that is forked. This means that when we abort
                    # one of them, we kill the clock that do_animation_sequence is running on, thereby aborting all
                    # remaining segments as well. This is exactly what we want: if we call change_note_parameter while
                    # previous change_note_parameter is running, we want to abort all segments of the one that's running
                    try:
                        this_segment.run(silent="silent" in note_info["flags"])
                    except Exception as e:
                        raise e

            clock.fork(do_animation_sequence, name="PARAM_ANIMATION({})".format(param_name))
        else:
            parameter_change_segment = ParameterChangeSegment(
                parameter_change_function, note_info["parameter_values"][param_name], target_value_or_values,
                transition_length_or_lengths, transition_curve_shape_or_shapes, clock, call_priority,
                temporal_resolution=temporal_resolution)
            with note_info["segments_list_lock"]:
                segments_list.append(parameter_change_segment)
            clock.fork(parameter_change_segment.run, kwargs={"silent": "silent" in note_info["flags"]})

    def change_note_pitch(self, note_id, target_value_or_values: Union[Sequence, Number],
                          transition_length_or_lengths: Union[Sequence, Number] = 0,
                          transition_curve_shape_or_shapes: Union[Sequence, Number] = 0, clock="auto"):
        self.change_note_parameter(note_id, "pitch", target_value_or_values, transition_length_or_lengths,
                                   transition_curve_shape_or_shapes, clock)

    def change_note_volume(self, note_id, target_value_or_values: Union[Sequence, Number],
                           transition_length_or_lengths: Union[Sequence, Number] = 0,
                           transition_curve_shape_or_shapes: Union[Sequence, Number] = 0, clock="auto"):
        self.change_note_parameter(note_id, "volume", target_value_or_values, transition_length_or_lengths,
                                   transition_curve_shape_or_shapes, clock)

    def split_note(self, note_id, clock="auto"):
        """
        Adds a split point in a note, causing it later to be rendered as tied pieces.
        :param note_id: Which note or NoteHandle to split
        :param clock: Probably shouldn't ever need to mess with this. The clock is used to generate a TimeStamp, so
        all clocks in the same family will lead to the same result.
        """
        clock = ScampInstrument._resolve_clock_argument(clock)

        note_id = note_id.note_id if isinstance(note_id, NoteHandle) else note_id
        note_info = self._note_info_by_id[note_id]
        note_info["split_points"].append(TimeStamp(clock))

    def end_note(self, note_id=None, clock="auto"):
        """
        Ends the note with the given note id. If none is specified, it ends the note we started longest ago.
        Note that this only applies to notes started in an open-ended way with 'start_note', notes created
        using play_note have their lifecycle controlled automatically.
        :param note_id: either the id itself or a NoteHandle with that id
        :param clock: just used to capture the ending TimeStamp
        """
        clock = ScampInstrument._resolve_clock_argument(clock)

        # in case we're passed a NoteHandle instead of an actual id number, get the number from the handle
        note_id = note_id.note_id if isinstance(note_id, NoteHandle) else note_id

        if note_id is not None:
            # as specific note_id has been given, so it had better belong to a currently playing note!
            if note_id not in self._note_info_by_id:
                logging.warning("Tried to end a note that was never started!")
                return
        elif len(self._note_info_by_id) > 0:
            # no specific id was given, so end the oldest note
            # (note that ids just count up, so the lowest active id is the oldest)
            note_id = min(self._note_info_by_id.keys())
        else:
            logging.warning("Tried to end a note that was never started!")
            return

        # end any segments that are still changing
        note_info = self._note_info_by_id[note_id]
        for param_name in note_info["parameter_change_segments"]:
            if len(note_info["parameter_change_segments"][param_name]) > 0:
                note_info["parameter_change_segments"][param_name][-1].abort_if_running()

        # transcribe the note, if applicable
        note_info["end_time"] = TimeStamp(clock)
        if "no_transcribe" not in note_info["flags"]:
            for transcriber in self._transcribers_to_notify:
                transcriber.register_note(self, note_info)

        # do the sonic implementation of ending the note, as long as it's not silent
        if "silent" not in note_info["flags"]:
            for playback_implementation in self. playback_implementations:
                playback_implementation.end_note(note_id)

        # remove from active notes and delete the note info
        del self._note_info_by_id[note_id]

    def end_all_notes(self):
        """
        Ends all notes currently playing
        """
        while len(self._note_info_by_id) > 0:
            self.end_note()

    def num_notes_playing(self):
        """
        Returns the number of notes currently playing.
        """
        return len(self._note_info_by_id)

    """
    ---------------------------------------- Adding and removing playback ----------------------------------------
    """

    def add_soundfont_playback(self, bank_and_preset=(0, 0), soundfont="default", num_channels=8,
                               audio_driver="default", max_pitch_bend="default"):
        SoundfontPlaybackImplementation(self, bank_and_preset, soundfont, num_channels,
                                        audio_driver=audio_driver, max_pitch_bend=max_pitch_bend)
        return self

    def remove_soundfont_playback(self):
        for index in reversed(range(len(self.playback_implementations))):
            if isinstance(self.playback_implementations[index], SoundfontPlaybackImplementation):
                self.playback_implementations.pop(index)
                break
        return self

    def add_streaming_midi_playback(self, midi_output_device="default", num_channels=8,
                                    midi_output_name=None, max_pitch_bend="default"):
        MIDIStreamPlaybackImplementation(self, midi_output_device, num_channels, midi_output_name, max_pitch_bend)
        return self

    def remove_streaming_midi_playback(self):
        for index in reversed(range(len(self.playback_implementations))):
            if isinstance(self.playback_implementations[index], MIDIStreamPlaybackImplementation):
                self.playback_implementations.pop(index)
                break
        return self

    def add_osc_playback(self, port, ip_address="127.0.0.1", message_prefix=None, osc_message_addresses="default"):
        OSCPlaybackImplementation(self, port, ip_address, message_prefix, osc_message_addresses)
        return self

    def remove_osc_playback(self):
        for index in reversed(range(len(self.playback_implementations))):
            if isinstance(self.playback_implementations[index], OSCPlaybackImplementation):
                self.playback_implementations.pop(index)
                break
        return self

    """
    ------------------------------------------------- Other -----------------------------------------------------
    """

    def set_max_pitch_bend(self, semitones):
        for playback_implementation in self.playback_implementations:
            playback_implementation.set_max_pitch_bend(semitones)

    @property
    def default_spelling_policy(self):
        return self._default_spelling_policy

    @default_spelling_policy.setter
    def default_spelling_policy(self, value):
        if value is None or isinstance(value, SpellingPolicy):
            self._default_spelling_policy = value
        elif isinstance(value, str):
            self._default_spelling_policy = SpellingPolicy.from_string(value)
        else:
            raise ValueError("Spelling policy not understood.")

    @staticmethod
    def _resolve_clock_argument(clock):
        """
        Just a really common code fragment, so I made it a static method.
        Takes the clock argument given to a playback method, resolves it using current_clock() if "auto", and
        generates a new master clock if still none (i.e. if "None" was passed explicitly, or if current_clock()
        returns "None", since there isn't an active clock.
        """
        clock = current_clock() if clock == "auto" else clock
        if clock is None:
            clock = Clock()
        return clock

    """
    --------------------------------------------- To / from JSON -------------------------------------------------
    """

    def to_json(self):
        return {
            "name": self.name,
            "playback_implementations": [playback_implementation.to_json()
                                         for playback_implementation in self.playback_implementations],
            "default_spelling_policy": self.default_spelling_policy
        }

    @classmethod
    def from_json(cls, json_object, ensemble=None):
        """
        :param json_object: the json object we're loading from
        :param ensemble: this allows us to pass the ensemble to the instruments we're reconstructing when we're
        reconstructing an ensemble from json.
        """
        assert isinstance(json_object, dict)
        instrument = cls(json_object["name"] if "name" in json_object else None, ensemble=ensemble)
        instrument.default_spelling_policy = json_object["default_spelling_policy"]
        for playback_implementation_json in json_object["playback_implementations"]:
            for playback_implementation_type in iterate_all_subclasses(PlaybackImplementation):
                if playback_implementation_json["type"] == playback_implementation_type.__name__:
                    playback_implementation_type.from_json(playback_implementation_json, host_instrument=instrument)
                    break
        return instrument

    def __repr__(self):
        return "ScampInstrument.from_json({})".format(self.to_json())
