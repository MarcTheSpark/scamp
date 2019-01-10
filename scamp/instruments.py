import threading
import time
from . import Envelope
from .utilities import SavesToJSON
from itertools import count
from .settings import playback_settings
from copy import deepcopy
from .note_properties import NotePropertiesDictionary
from clockblocks import current_clock
from .spelling import SpellingPolicy
import atexit
from .dependencies import udp_client

# TODO: Stretch goal: allow MIDIScampInstrument to have multiple presets
# Maybe create a method "add_alternate_preset(name, preset, soundfont_index, num_channels, triggers)"
# that sets aside extra channels for it. Triggers could be of the form "articulation:staccato" or something
# like that. But also if properties contains an entry for "preset:{preset name}" that could trigger it
# as well.


class ScampInstrument(SavesToJSON):

    def __init__(self, host=None, name=None):
        """
        This is the parent class used all kinds of instruments used within an ensemble. The most basic one, below,
        called a MidiScampInstrument, uses fluidsynth to playback sounds from a soundfont, and also sends the
        output to a port via rtmidi. Other implementations could playback sounds in a different way.
        :param host: The Session or Ensemble that this instrument acts within
        :param name: The name of this instrument (used later in labeling parts in output)
        """
        self.name = name
        self.name_count = None
        self.host_ensemble = None

        if host is not None:
            self.set_host(host)

        # A policy for spelling notes used as the default for this instrument. Overrides the session default.
        self._default_spelling_policy = None

        # used to identify instruments uniquely, even if they're given the same name
        self._notes_started = []   # each entry goes (note_id, pitch, volume, start_time, variant_dictionary)
        self._performance_part = None

    def set_host(self, host):
        from .session import Session
        from .ensemble import Ensemble
        assert isinstance(host, (Session, Ensemble)), "ScampInstrument must be hosted by Ensemble or Session"
        if isinstance(host, Session):
            self.host_ensemble = host.ensemble
        else:
            self.host_ensemble = host
        self.name_count = self.host_ensemble.get_part_name_count(self.name)

    def time(self):
        if self.host_ensemble is not None and self.host_ensemble.host_session is not None:
            return self.host_ensemble.host_session.time()
        else:
            return time.time()

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

    def to_json(self):
        return {
            "type": "ScampInstrument",
            "name": self.name,
        }

    # -------------- Reconstruct from JSON (doesn't need subclass reimplementation) ---------------

    @staticmethod
    def from_json(json_dict, host_ensemble=None):
        # the 'type' argument of the json_dict tells us which kind of ScampInstrument constructor to use
        type_to_create = None
        for instrument_type in ScampInstrument.__subclasses__():
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

    def _convert_properties_to_dictionary(self, raw_properties):
        properties = NotePropertiesDictionary.from_unknown_format(raw_properties) \
            if not isinstance(raw_properties, NotePropertiesDictionary) else raw_properties
        if properties["spelling_policy"] is None:
            if self.default_spelling_policy is not None:
                properties.spelling_policy = self.default_spelling_policy
            elif self.host_ensemble is not None and self.host_ensemble.host_session is not None \
                    and self.host_ensemble.host_session.default_spelling_policy is not None:
                properties.spelling_policy = self.host_ensemble.host_session.default_spelling_policy
        return properties

    def _do_play_note(self, pitch, volume, length, properties, clock=None):
        # Does the actual sonic implementation of playing a note; used as a thread by the public method "play_note"
        note_start_time = time.time()
        # convert lists to Envelopes
        is_animating_volume = isinstance(volume, Envelope)
        is_animating_pitch = isinstance(pitch, Envelope)
        # the starting volume (velocity) of the note needs to be as loud as the note is ever going to get
        start_volume = volume.max_level() if isinstance(volume, Envelope) else volume
        # the starting pitch should just be whatever it is
        start_pitch = pitch.value_at(0) if isinstance(pitch, Envelope) else pitch

        note_id = self._do_start_note(start_pitch, start_volume, properties)
        if is_animating_volume or is_animating_pitch:
            temporal_resolution = float("inf")
            if is_animating_volume:
                volume_curve = volume.normalize_to_duration(length, False)
                temporal_resolution = min(temporal_resolution,
                                          MidiScampInstrument.get_good_volume_temporal_resolution(volume_curve))
            if is_animating_pitch:
                pitch_curve = pitch.normalize_to_duration(length, False)
                temporal_resolution = min(temporal_resolution,
                                          MidiScampInstrument.get_good_pitch_bend_temporal_resolution(pitch_curve))
            temporal_resolution = max(temporal_resolution, 0.01)  # faster than this is wasteful, doesn't seem to help

            def animate_pitch_and_volume():
                while note_start_time is not None:
                    try:
                        # Sometimes do_play_note ends and start_time gets set to None in the middle of
                        # the while loop, leading to a TypeError when we do time.time() - note_start_time
                        # this catches that possibility
                        if is_animating_volume:
                            # note that, since change_note_volume is affecting expression values, we need to send it
                            # the proportion of the start_volume rather than the absolute volume
                            self.change_note_volume(note_id,
                                                    volume_curve.value_at(time.time() - note_start_time) / start_volume)
                        if is_animating_pitch:
                            self.change_note_pitch(note_id, pitch_curve.value_at(time.time() - note_start_time))
                    except TypeError:
                        break

                    time.sleep(temporal_resolution)

            if temporal_resolution < length:  # catches the case of a static curve with infinite temporal_resolution
                if clock is not None:
                    clock.fork_unsynchronized(process_function=animate_pitch_and_volume)
                else:
                    threading.Thread(target=animate_pitch_and_volume, daemon=True).start()

        time.sleep(length)
        # cut off any pitch or volume animation thread by setting the start_time to None
        note_start_time = None

        self._do_end_note(note_id)

    @staticmethod
    def get_good_pitch_bend_temporal_resolution(pitch_envelope):
        """
        Returns a reasonable temporal resolution
        :type pitch_envelope: Envelope
        """
        max_cents_per_second = pitch_envelope.max_absolute_slope() * 100
        # cents / update * updates / sec = cents / sec   =>  updates_freq = cents_per_second / cents_per_update
        # we'll aim for 4 cents per update, since some say the JND is 5-6 cents
        update_freq = max_cents_per_second / 4.0
        return 1 / update_freq

    @staticmethod
    def get_good_volume_temporal_resolution(volume_envelope):
        """
        Returns a reasonable temporal resolution
        :type volume_envelope: Envelope
        """
        max_volume_per_second = volume_envelope.max_absolute_slope()
        # no point in updating faster than the number of ticks per second
        update_freq = max_volume_per_second * 127
        return 1 / update_freq

    # ------------------------- "Public" Playback Methods -------------------------

    def play_note(self, pitch, volume, length, properties=None, blocking=True, clock=None):
        """
        Play a note
        :param pitch: The midi pitch of the note. Can be floating-point, can be a list or Envelope.
        :param volume: The volume, in a normalized range 0 to 1. Can be a list or Envelope.
        :param length: The length of the note with respect to the clock used (seconds if no clock is used).
        :param properties: A dictionary of properties about this note
        :param blocking: blocks the current thread until done playing
        :param clock: The clock within which this note is played. If none, we check if a clock has been defined on this
        thread by setting threading.current_thread().__clock__ and use that. If no clocks at all, uses seconds.
        :return: None
        """

        if clock is None and hasattr(threading.current_thread(), "__clock__"):
            clock = threading.current_thread().__clock__

        properties = self._convert_properties_to_dictionary(properties)

        volume = Envelope.from_list(volume) if hasattr(volume, "__len__") else volume
        pitch = Envelope.from_list(pitch) if hasattr(pitch, "__len__") else pitch

        # record the note in the hosting session, if it's recording
        if self._performance_part is not None:
            from .performance import PerformancePart
            assert isinstance(self._performance_part, PerformancePart)
            pc = self.host_ensemble.host_session
            length_factor = (1 if pc._recording_clock == "absolute" else pc._recording_clock.absolute_rate()) / \
                            clock.absolute_rate()
            recorded_length = tuple(x * length_factor for x in length) \
                if hasattr(length, "__len__") else length * length_factor
            recorded_length_sum = sum(recorded_length) if hasattr(recorded_length, "__len__") else recorded_length

            if isinstance(pitch, Envelope):
                pitch.normalize_to_duration(recorded_length_sum)
            if isinstance(volume, Envelope):
                volume.normalize_to_duration(recorded_length_sum)
            self._performance_part.new_note(pc.get_recording_beat(), recorded_length, pitch, volume, properties)

        # now that we've notated the length, we collapse it if it's a tuple
        length = sum(length) if hasattr(length, "__len__") else length

        # apply explicit playback adjustments, as well as those implied by articulations and other notations
        unaltered_length = length
        pitch, volume, length = properties.apply_playback_adjustments(pitch, volume, length)

        # Note that, even if there's a clock involved we run _do_play_note in a simple thread rather than a sub-clock.
        # That is because the overhead of running in a clock is high for small sleep values like animation of pitch and
        # volume, and it gets way behind. Better to just use a parallel Thread and adjust the length
        if clock is not None:
            if not clock.is_fast_forwarding():
                # note that if we're fast-forwarding we don't want to play the note
                # we do still want to call wait below to advance time (no sleeping will happen on the master clock)
                clock.fork_unsynchronized(process_function=self._do_play_note,
                                          args=(pitch, volume, length / clock.absolute_rate(), properties, clock))
            if blocking:
                clock.wait(unaltered_length)
        else:
            threading.Thread(target=self._do_play_note, args=(pitch, volume, length, properties)).start()
            if blocking:
                time.sleep(unaltered_length)

    def play_chord(self, pitches, volume, length, properties=None, blocking=True, clock=None):
        """
        Simple utility for playing chords without having to play notes with blocking=False
        Takes a list of pitches, and passes them to play_note
        """
        assert hasattr(pitches, "__len__")

        properties = self._convert_properties_to_dictionary(properties)

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

    def start_note(self, pitch, volume, properties=None):
        """
        Starts a note 'manually', meaning that its length is not predetermined, and that it has to be manually ended
        later by calling 'end_note' or 'end_all_notes'
        """
        properties = self._convert_properties_to_dictionary(properties)
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
        if self._performance_part is not None and start_time >= self.host_ensemble.host_session.recording_start_time:
            self._performance_part.new_note(
                start_time - self.host_ensemble.host_session.recording_start_time,
                self.time() - start_time, pitch, volume, properties
            )

    def end_all_notes(self):
        """
        Ends all notes that have been manually started with 'start_note'
        """
        while len(self._notes_started) > 0:
            self.end_note()

    def num_notes_playing(self):
        """
        Returns the number of notes currently playing that were manually started with 'start_note'
        """
        return len(self._notes_started)

    def __repr__(self):
        return "ScampInstrument({}, {})".format(self.host_ensemble, self.name)


# -------------------------------------------- MIDIScampInstrument ---------------------------------------------


class MidiScampInstrument(ScampInstrument):

    def __init__(self, host=None, name=None, preset=(0, 0), soundfont_index=0, num_channels=8,
                 midi_output_device=None, midi_output_name=None):
        if host is None:
            raise ValueError("MidiScampInstrument must be instantiated "
                             "within the context of an Ensemble or Session")
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

        self.set_max_pitch_bend(playback_settings.default_max_midi_pitch_bend)

        # keep track of what notes are currently playing
        # each entry is an identifying tuple of: (channel, pitch, unique_id)
        self.active_midi_notes = []
        self.note_start_lock = threading.Lock()

    # ---- The constituent parts of the _do_play_note call ----

    def _do_play_note(self, pitch, volume, length, properties, clock=None):
        # _do_start_note needs to know whether or not the pitch changes, since pitch bends need to
        # be placed on separate channels. We'll pass along that info by placing it in the properties
        # dictionary, but we make a copy first so as not to alter the dictionary we're given
        properties["temp"]["pitch changes"] = isinstance(pitch, Envelope)
        super()._do_play_note(pitch, volume, length, properties, clock)

    def start_note(self, pitch, volume, properties=None, pitch_might_change=True):
        # Same as with _do_play_note, we need to set the "pitch changes" key in the properties dictionary
        # since we don't know if the pitch will change, the default is to assume it does. If the user knows it
        # won't change pitch, then they can set pitch_might_change to false for more efficient MIDI channel use
        properties = self._convert_properties_to_dictionary(properties)
        properties["temp"]["pitch changes"] = isinstance(pitch, Envelope)
        return super().start_note(pitch, volume, properties)

    def _do_start_note(self, pitch, volume, properties):
        # Does the actual sonic implementation of starting a note
        # in this case the note_id returned will be a tuple consisting of
        # the channel, the midi key pressed, the start time, and whether or not pitch bend is used
        int_pitch = int(round(pitch))
        uses_pitch_bend = (pitch != int_pitch) or properties["temp"]["pitch changes"]

        with self.note_start_lock:
            channel = self._find_channel_for_note(int_pitch, new_note_uses_bend=uses_pitch_bend)
            note_id = channel, int_pitch, self.time(), uses_pitch_bend
            self.active_midi_notes.append(note_id)

        self.midi_instrument.pitch_bend(channel, pitch - int_pitch)
        self.midi_instrument.note_on(channel, int_pitch, volume)

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

            # we need to consider this note active for an additional half second or so after the note_off
            # since the release trail is still going. This avoids accidentally pitch-shifting the release trail
            def remove_from_active_midi_notes():
                time.sleep(0.5)
                try:
                    self.active_midi_notes.remove(note_id)
                except ValueError:
                    pass

            if current_clock() is not None:
                current_clock().fork_unsynchronized(process_function=remove_from_active_midi_notes)
            else:
                threading.Thread(target=remove_from_active_midi_notes).start()

    def change_note_pitch(self, note_id, new_pitch):
        # Changes the pitch of the note started at channel
        channel, int_pitch, note_start_time, uses_pitch_bend = note_id
        self.midi_instrument.pitch_bend(channel, new_pitch - int_pitch)

    def change_note_volume(self, note_id, new_volume):
        """
        Changes the volume of the note with the given id
        For a MidiScampInstrument, this is mapped to expression, which means that new_volume represents a
        proportion of the starting volume of the note. The note can't get louder than it started.
        """
        channel, int_pitch, note_start_time, uses_pitch_bend = note_id
        self.midi_instrument.expression(channel, new_volume)

    def set_max_pitch_bend(self, semitones):
        self.midi_instrument.set_max_pitch_bend(semitones)

    def to_json(self):
        return {
            "type": "MidiScampInstrument",
            "name": self.name,
            "preset": self.preset,
            "soundfont_index": self.soundfont_index,
            "num_channels": self.num_channels,
            # note that this saves the parameters we gave it explicitly, but not what it defaults to if
            # those parameters were left as None. That's good, because None should mean that it takes
            # on the defaults of whatever Ensemble / Session it's part of
            "midi_output_device": self.midi_output_device,
            "midi_output_name": self.midi_output_name
        }

    def __repr__(self):
        return "MidiScampInstrument({}, {}, {}, {}, {}, {}, {})".format(
            self.host_ensemble, self.name, self.preset, self.soundfont_index,
            self.num_channels, self.midi_output_device, self.midi_output_name
        )


# -------------------------------------------- OSCScampInstrument ----------------------------------------------
# TODO: OSCScampInstrument._currently playing duplicates some functionality from
# ScampInstrument._notes_started   Fix that?

_note_id_generator = count()


class OSCScampInstrument(ScampInstrument):

    def __init__(self, host=None, name=None, port=None, ip_address="127.0.0.1", message_prefix=None,
                 osc_message_addresses="default"):
        super().__init__(host, name)

        # the output client for OSC messages
        # by default the IP address is the local 127.0.0.1
        self.ip_address = ip_address
        assert port is not None, "OSCScampInstrument must set an output port."
        self.port = port
        self.client = udp_client.SimpleUDPClient(ip_address, port)
        # the first part of the osc message; used to distinguish between instruments
        # by default uses the name of the instrument, but if two instruments have the same name, this is bad
        self.message_prefix = (name if name is not None else "unnamed") if message_prefix is None else message_prefix

        self._start_note_message = osc_message_addresses["start_note"] \
            if isinstance(osc_message_addresses, dict) and "start_note" in osc_message_addresses \
            else playback_settings.osc_message_addresses["start_note"]
        self._end_note_message = osc_message_addresses["end_note"] \
            if isinstance(osc_message_addresses, dict) and "end_note" in osc_message_addresses \
            else playback_settings.osc_message_addresses["end_note"]
        self._change_pitch_message = osc_message_addresses["change_pitch"] \
            if isinstance(osc_message_addresses, dict) and "change_pitch" in osc_message_addresses \
            else playback_settings.osc_message_addresses["change_pitch"]
        self._change_volume_message = osc_message_addresses["change_volume"] \
            if isinstance(osc_message_addresses, dict) and "change_volume" in osc_message_addresses \
            else playback_settings.osc_message_addresses["change_volume"]
        self._change_quality_message = osc_message_addresses["change_quality"] \
            if isinstance(osc_message_addresses, dict) and "change_quality" in osc_message_addresses \
            else playback_settings.osc_message_addresses["change_quality"]

        self._currently_playing = []

        def clean_up():
            for note_id in self._currently_playing:
                self._do_end_note(note_id)

        atexit.register(clean_up)

    # ---- The constituent parts of the _do_play_note call ----

    def _do_play_note(self, pitch, volume, length, properties, clock=None):
        # This extra bit of implementation for _do_play_note allows us to animate extra qualities that are
        # defined by Envelope values in properties["qualities"]. It's kind of ugly, but it works.

        if "qualities" in properties and isinstance(properties["qualities"], dict):
            start_time = time.time()
            qualities_being_animated = {}
            for quality in properties["qualities"]:
                # if we're given an Envelope in the form of a list, convert it to a Envelope object
                if isinstance(properties["qualities"][quality], list):
                    properties["qualities"][quality] = Envelope.from_list(properties["qualities"][quality])
                value = properties["qualities"][quality]
                if isinstance(value, Envelope):
                    qualities_being_animated[quality] = value.normalize_to_duration(length, False)
            if len(qualities_being_animated) > 0:
                properties["_osc_note_id"] = next(_note_id_generator)

                def animate_qualities():
                    while start_time is not None:
                        time.sleep(0.01)  # we sleep first, since we set the property at the beginning
                        try:
                            # Sometimes do_play_note ends and start_time gets set to None in the middle of
                            # the while loop, leading to a TypeError when we do time.time() - start_time
                            # this catches that possibility
                            for animated_quality in qualities_being_animated:
                                self.change_note_quality(
                                    properties["_osc_note_id"], animated_quality,
                                    qualities_being_animated[animated_quality].value_at(time.time() - start_time)
                                )
                        except TypeError:
                            break

                if clock is not None:
                    clock.fork_unsynchronized(process_function=animate_qualities)
                else:
                    threading.Thread(target=animate_qualities, daemon=True).start()

        super()._do_play_note(pitch, volume, length, properties, clock)
        start_time = None

    def _do_start_note(self, pitch, volume, properties):
        note_id = properties["_osc_note_id"] if "_osc_note_id" in properties else next(_note_id_generator)
        self.client.send_message("/{}/{}".format(self.message_prefix, self._start_note_message),
                                 [note_id, pitch, volume])

        if "qualities" in properties and isinstance(properties["qualities"], dict):
            for quality in properties["qualities"]:
                value = properties["qualities"][quality]
                if isinstance(value, Envelope):
                    self.change_note_quality(note_id, quality, value.value_at(0))
                else:
                    self.change_note_quality(note_id, quality, value)

        self._currently_playing.append(note_id)
        return note_id

    def _do_end_note(self, note_id):
        self.client.send_message("/{}/{}".format(self.message_prefix, self._end_note_message), [note_id])
        if note_id in self._currently_playing:
            self._currently_playing.remove(note_id)

    def change_note_pitch(self, note_id, new_pitch):
        self.client.send_message("/{}/{}".format(self.message_prefix, self._change_pitch_message),
                                 [note_id, new_pitch])

    def change_note_volume(self, note_id, new_volume):
        self.client.send_message("/{}/{}".format(self.message_prefix, self._change_volume_message),
                                 [note_id, new_volume])

    def change_note_quality(self, note_id, quality, value):
        self.client.send_message("/{}/{}/{}".format(self.message_prefix, self._change_quality_message, quality),
                                 [note_id, value])

    def to_json(self):
        return {
            "type": "OSCScampInstrument",
            "name": self.name,
            "port": self.port,
            "ip_address": self.ip_address,
            "message_prefix": self.message_prefix,
            "osc_message_addresses": {
                "start_note": self._start_note_message,
                "end_note": self._end_note_message,
                "change_pitch": self._change_pitch_message,
                "change_volume": self._change_volume_message,
                "change_quality": self._change_quality_message
            },
        }

    def __repr__(self):
        return "OSCScampInstrument({}, {}, {}, {}, {})".format(
            self.host_ensemble, self.name, self.port, self.ip_address,
            self.message_prefix, {
                "start_note": self._start_note_message,
                "end_note": self._end_note_message,
                "change_pitch": self._change_pitch_message,
                "change_volume": self._change_volume_message,
                "change_quality": self._change_quality_message
            }
        )
