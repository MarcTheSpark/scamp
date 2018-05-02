import threading
import time
from .parameter_curve import ParameterCurve
import logging
from .utilities import SavesToJSON


class PlaycorderInstrument(SavesToJSON):

    def __init__(self, host=None, name=None):
        """
        This is the parent class used all kinds of instruments used within a playcorder. The most basic one, below,
        called a MidiPlaycorderInstrument, uses fluidsynth to playback sounds from a soundfont, and also sends the
        output to a port via rtmidi. Other implementations could playback sounds in a different way.
        :param host: The Playcorder or Ensemble that this instrument acts within
        :param name: The name of this instrument (used later in labeling parts in output)
        """
        self.name = name
        self.name_count = None
        self.host_ensemble = None
        if host is not None:
            self.set_host(host)

        # used to identify instruments uniquely, even if they're given the same name
        self._notes_started = []   # each entry goes (note_id, pitch, volume, start_time, variant_dictionary)
        self._performance_part = None

    def set_host(self, host):
        from .playcorder import Playcorder
        from .ensemble import Ensemble
        assert isinstance(host, (Playcorder, Ensemble))
        if isinstance(host, Playcorder):
            self.host_ensemble = host.ensemble
        else:
            self.host_ensemble = host
        self.name_count = self.host_ensemble.get_part_name_count(self.name)

    def _viable(self):
        if self.host_ensemble is None:
            logging.warning("Instrument tried to play, but was not part of an Ensemble.")
            return False
        else:
            return True

    def time(self):
        if self.host_ensemble is not None and self.host_ensemble.host_playcorder is not None:
            return self.host_ensemble.host_playcorder.time()
        else:
            return time.time()

    # ------------------ Methods to be implemented by subclasses ------------------

    def _do_start_note(self, pitch, volume, properties):
        # Does the actual sonic implementation of starting a note
        # should return the note_id, which is used to keep track of the note
        pass

    def _do_end_note(self, note_id):
        # Does the actual sonic implementation of ending a the note with the given id
        pass

    def change_note_pitch(self, note_id, new_pitch):
        # Changes the pitch of the note with the given id
        pass

    def change_note_volume(self, note_id, new_volume):
        # Changes the expression of the note with the given id
        pass

    def _to_json(self):
        return {
            "type": "PlaycorderInstrument",
            "name": self.name,
        }

    # -------------- Reconstruct from JSON (doesn't need subclass reimplementation) ---------------

    @staticmethod
    def _from_json(json_dict, host_ensemble=None):
        # the 'type' argument of the json_dict tells us which kind of PlaycorderInstrument constructor to use
        type_to_create = None
        for instrument_type in PlaycorderInstrument.__subclasses__():
            if json_dict["type"] == instrument_type.__name__:
                type_to_create = instrument_type
                break
        if type_to_create is None:
            raise ValueError("Trying to reconstruct instrument of type {}, "
                             "but that type is not defined.".format(json_dict["type"]))
        kwargs = dict(json_dict)
        del kwargs["type"]
        return type_to_create(host_ensemble, **kwargs)

    # ------------------------- "Private" Playback Methods -----------------------

    def _do_play_note(self, pitch, volume, length, properties, clock=None):
        # Does the actual sonic implementation of playing a note; used as a thread by the public method "play_note"
        note_start_time = time.time()
        # convert lists to ParameterCurves
        is_animating_volume = isinstance(volume, ParameterCurve)
        is_animating_pitch = isinstance(pitch, ParameterCurve)
        # the starting volume (velocity) of the note needs to be as loud as the note is ever going to get
        start_volume = volume.max_level() if isinstance(volume, ParameterCurve) else volume
        # the starting pitch should just be whatever it is
        start_pitch = pitch.value_at(0) if isinstance(pitch, ParameterCurve) else pitch

        note_id = self._do_start_note(start_pitch, start_volume, properties)
        if is_animating_volume or is_animating_pitch:
            temporal_resolution = float("inf")
            if is_animating_volume:
                volume_curve = volume.normalize_to_duration(length, False)
                temporal_resolution = min(temporal_resolution,
                                          MidiPlaycorderInstrument.get_good_volume_temporal_resolution(volume_curve))
            if is_animating_pitch:
                pitch_curve = pitch.normalize_to_duration(length, False)
                temporal_resolution = min(temporal_resolution,
                                          MidiPlaycorderInstrument.get_good_pitch_bend_temporal_resolution(pitch_curve))
            temporal_resolution = max(temporal_resolution, 0.01)  # faster than this is wasteful, doesn't seem to help

            def animate_pitch_and_volume():
                while note_start_time is not None:
                    if is_animating_volume:
                        # note that, since change_note_volume is affecting expression values, we need to send it
                        # the proportion of the start_volume rather than the absolute volume
                        self.change_note_volume(note_id,
                                                volume_curve.value_at(time.time() - note_start_time) / start_volume)
                    if is_animating_pitch:
                        self.change_note_pitch(note_id, pitch_curve.value_at(time.time() - note_start_time))

                    time.sleep(temporal_resolution)

            if clock is not None:
                clock.fork_unsynchronized(process_function=animate_pitch_and_volume)
            else:
                threading.Thread(target=animate_pitch_and_volume, daemon=True).start()

        time.sleep(length)
        # cut off any pitch or volume animation thread by setting the start_time to None
        note_start_time = None

        self._do_end_note(note_id)

    @staticmethod
    def get_good_pitch_bend_temporal_resolution(pitch_param_curve):
        """
        Returns a reasonable temporal resolution
        :type pitch_param_curve: ParameterCurve
        """
        max_cents_per_second = pitch_param_curve.max_absolute_slope() * 100
        # cents / update * updates / sec = cents / sec   =>  updates_freq = cents_per_second / cents_per_update
        # we'll aim for 4 cents per update, since some say the JND is 5-6 cents
        update_freq = max_cents_per_second / 4.0
        return 1 / update_freq

    @staticmethod
    def get_good_volume_temporal_resolution(volume_param_curve):
        """
        Returns a reasonable temporal resolution
        :type volume_param_curve: ParameterCurve
        """
        max_volume_per_second = volume_param_curve.max_absolute_slope()
        # no point in updating faster than the number of ticks per second
        update_freq = max_volume_per_second * 127
        return 1 / update_freq

    # ------------------------- "Public" Playback Methods -------------------------

    @staticmethod
    def _make_properties_dict(properties):
        # TODO: can take a string, a list, or a dict and turn it into a standardized dict of note properties
        if properties is None:
            return {}
        return properties

    def play_note(self, pitch, volume, length, properties=None, blocking=False, clock=None):
        """
        Play a note
        :param pitch: The midi pitch of the note. Can be floating-point, can be a list or Parameter curve.
        :param volume: The volume, in a normalized range 0 to 1. Can be a list or Parameter curve.
        :param length: The length of the note with respect to the clock used (seconds if no clock is used).
        :param properties: A dictionary of properties about this note
        :param blocking: blocks the current thread until done playing
        :param clock: The clock within which this note is played. If none, we check if a clock has been defined on this
        thread by setting threading.current_thread().__clock__ and use that. If no clocks at all, uses seconds.
        :return: None
        """
        if not self._viable():
            return

        if clock is None and hasattr(threading.current_thread(), "__clock__"):
            clock = threading.current_thread().__clock__

        properties = PlaycorderInstrument._make_properties_dict(properties)
        volume = ParameterCurve.from_list(volume) if hasattr(volume, "__len__") else volume
        pitch = ParameterCurve.from_list(pitch) if hasattr(pitch, "__len__") else pitch

        # record the note in the hosting playcorder, if it's recording
        if self._performance_part is not None:
            from .performance import PerformancePart
            assert isinstance(self._performance_part, PerformancePart)
            pc = self.host_ensemble.host_playcorder
            recorded_length = length / clock.absolute_rate() * \
                (1 if pc._recording_clock == "absolute" else pc._recording_clock.absolute_rate())
            self._performance_part.new_note(pc.get_recording_beat(), recorded_length, pitch, volume, properties)

        # Note that, even if there's a clock involved we run _do_play_note in a simple thread rather than a sub-clock.
        # That is because the overhead of running in a clock is high small sleep values like animation ot pitch and
        # volume, and it gets way behind. Better to just use a parallel Thread and adjust the length
        if clock is not None:
            if not clock.is_fast_forwarding():
                # note that if we're fast-forwarding we don't want to play the note
                # we do still want to call wait below to advance time (no sleeping will happen on the master clock)
                clock.fork_unsynchronized(process_function=self._do_play_note,
                                          args=(pitch, volume, length / clock.absolute_rate(), properties, clock))
            if blocking:
                clock.wait(length)
        else:
            if blocking:
                self._do_play_note(pitch, volume, length, properties)
            else:
                threading.Thread(target=self._do_play_note, args=(pitch, volume, length, properties)).start()

    def start_note(self, pitch, volume, properties=None):
        """
        Starts a note 'manually', meaning that its length is not predetermined, and that it has to be manually ended
        later by calling 'end_note' or 'end_all_notes'
        """
        if not self._viable():
            return
        properties = PlaycorderInstrument._make_properties_dict(properties)
        note_id = self._do_start_note(pitch, volume, properties)
        self._notes_started.append((note_id, pitch, volume, self.time(), properties))
        # returns the note_id as a reference, in case we want to change pitch mid-playback
        return note_id

    def end_note(self, note_id=None):
        """
        Ends the note with the given note id. If none is specified, it ends the note we started longest ago.
        Note that this only applies to notes started in an open-ended way with 'start_note', notes created
        using play_note have their lifecycle controlled automatically.
        """
        if not self._viable():
            return
        note_to_end = None
        if note_id is not None:
            # find the note referred to in the notes_started list
            for started_note in self._notes_started:
                if started_note[0] == note_id:
                    note_to_end = started_note
                    break
            if note_to_end is not None:
                self._notes_started.remove(note_to_end)
        elif len(self._notes_started) > 0:
            # if no note_id is specified, just end the note that has been going the longest
            note_to_end = self._notes_started.pop(0)

        if note_to_end is None:
            # no appropriate note has been found to end
            return

        note_id, pitch, volume, start_time, properties = note_to_end
        # call the specific implementation to stop the note
        self._do_end_note(note_id)

        # save to performance part if we're recording, and we have been since the note started
        if self._performance_part is not None and start_time >= self.host_ensemble.host_playcorder.recording_start_time:
            self._performance_part.new_note(
                start_time - self.host_ensemble.host_playcorder.recording_start_time,
                self.time() - start_time, pitch, volume, properties
            )

    def end_all_notes(self):
        """
        Ends all notes that have been manually started with 'start_note'
        """
        if not self._viable():
            return
        while len(self._notes_started) > 0:
            self.end_note()

    def num_notes_playing(self):
        """
        Returns the number of notes currently playing that were manually started with 'start_note'
        """
        if not self._viable():
            return
        return len(self._notes_started)

    def __repr__(self):
        return "PlaycorderInstrument({}, {})".format(self.host_ensemble, self.name)


class MidiPlaycorderInstrument(PlaycorderInstrument):

    def __init__(self, host=None, name=None, preset=(0, 0), soundfont_index=0, num_channels=8,
                 midi_output_device=None, midi_output_name=None):
        if host is None:
            raise ValueError("MidiPlaycorderInstrument must be instantiated "
                             "within the context of an Ensemble or Playcorder")
        super().__init__(host, name)

        self.midi_player = self.host_ensemble.midi_player
        from .combined_midi_player import CombinedMidiPlayer
        assert isinstance(self.midi_player, CombinedMidiPlayer)
        self.preset = preset
        self.soundfont_index = soundfont_index
        self.num_channels = num_channels
        self.midi_output_name = name if midi_output_name is None else midi_output_name
        self.midi_output_device = midi_output_device

        self.midi_instrument = self.midi_player.add_instrument(num_channels, preset, soundfont_index,
                                                               self.midi_output_device, self.midi_output_name)
        self.num_channels = num_channels

        # keep track of what notes are currently playing
        # each entry is an identifying tuple of: (channel, pitch, unique_id)
        self.active_midi_notes = []

    # ---- The constituent parts of the _do_play_note call ----

    def _do_play_note(self, pitch, volume, length, properties, clock=None):
        # _do_start_note needs to know whether or not the pitch changes, since pitch bends need to
        # be placed on separate channels. We'll pass along that info by placing it in the properties
        # dictionary, but we make a copy first so as not to alter the dictionary we're given
        altered_properties = dict(properties)
        altered_properties["pitch changes"] = isinstance(pitch, ParameterCurve)
        super()._do_play_note(pitch, volume, length, altered_properties, clock)

    def _do_start_note(self, pitch, volume, properties):
        # Does the actual sonic implementation of starting a note
        # in this case the note_id returned will be a tuple consisting of
        # the channel, the midi key pressed, the start time, and whether or not pitch bend is used
        int_pitch = int(round(pitch))
        uses_pitch_bend = (pitch != int_pitch) or properties['pitch changes']
        channel = self._find_channel_for_note(int_pitch, new_note_uses_bend=uses_pitch_bend)
        self.midi_instrument.pitch_bend(channel, pitch - int_pitch)
        self.midi_instrument.note_on(channel, int_pitch, volume)
        note_id = channel, int_pitch, self.time(), uses_pitch_bend
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

    def _to_json(self):
        return {
            "type": "MidiPlaycorderInstrument",
            "name": self.name,
            "preset": self.preset,
            "soundfont_index": self.soundfont_index,
            "num_channels": self.num_channels,
            # note that this saves the parameters we gave it explicitly, but not what it defaults to if
            # those parameters were left as None. That's good, because None should mean that it takes
            # on the defaults of whatever Ensemble / Playcorder it's part of
            "midi_output_device": self.midi_output_device,
            "midi_output_name": self.midi_output_name
        }

    def __repr__(self):
        return "MidiPlaycorderInstrument({}, {}, {}, {}, {}, {}, {})".format(
            self.host_ensemble, self.name, self.preset, self.soundfont_index,
            self.num_channels, self.midi_output_device, self.midi_output_name
        )
