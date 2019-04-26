from .soundfont_host import *
from .simple_rtmidi_wrapper import *
from clockblocks import fork_unsynchronized
import time
from abc import ABC, abstractmethod
import atexit
from .dependencies import udp_client


class PlaybackImplementation(ABC):

    def __init__(self, host_instrument):
        # these get populated when the PlaybackImplementation is registered
        self.host_instrument = host_instrument
        # noinspection PyProtectedMember
        self.note_info_dict = host_instrument._note_info_by_id
        host_instrument.playback_implementations.append(self)
        # this is a fallback: if the instrument does not belong to an ensemble, it does not have
        # shared resources and so it will rely on its own privately held resources.
        self._resources = None

    """
    Methods for storing and accessing shared resources for the ensemble. For instance, SoundfontPlaybackImplementation
    uses this to store an instance of SoundfontHost. Only one instance of fluidsynth (and therefore SoundfontHost)
    needs to be running for all instruments in the ensemble, so this is a way of pooling that resource.
    """

    @property
    def resource_dictionary(self):
        if self.host_instrument.ensemble is None:
            # if this instrument is not part of an ensemble, it can't really have shared resources
            # instead, it creates a local resources dictionary and uses that
            if self._resources is None:
                self._resources = {}
            return self._resources
        else:
            # if this instrument is part of an ensemble, that ensemble holds the shared resources for all the
            # different playback implementations. Each playback implementation type has its own resource dictionary,
            # stored with its type as a key in the ensemble's shared resources dictionary. This way there can't be
            # name conflicts between different playback implementations
            if type(self) not in self.host_instrument.ensemble.shared_resources:
                self.host_instrument.ensemble.shared_resources[type(self)] = {}
            return self.host_instrument.ensemble.shared_resources[type(self)]

    def has_shared_resource(self, key):
        return key in self.resource_dictionary

    def get_shared_resource(self, key):
        return None if key not in self.resource_dictionary else self.resource_dictionary[key]

    def set_shared_resource(self, key, value):
        self.resource_dictionary[key] = value

    """
    Methods for storing and accessing shared resources for the ensemble. For instance, SoundfontPlaybackImplementation
    uses this to store an instance of SoundfontHost. Only one instance of fluidsynth (and therefore SoundfontHost)
    needs to be running for all instruments in the ensemble, so this is a way of pooling that resource.
    """

    @abstractmethod
    def start_note(self, note_id, pitch, volume, properties, other_parameter_values: dict = None):
        pass

    @abstractmethod
    def end_note(self, note_id):
        pass

    @abstractmethod
    def change_note_pitch(self, note_id, new_pitch):
        pass

    @abstractmethod
    def change_note_volume(self, note_id, new_volume):
        pass

    @abstractmethod
    def change_note_parameter(self, note_id, parameter_name, new_value):
        pass

    @abstractmethod
    def set_max_pitch_bend(self, semitones):
        # We include this because some playback implementations, namely ones that use the midi protocol, need a
        # way of changing the max pitch bend.
        pass

    @abstractmethod
    def to_json(self):
        pass

    @abstractmethod
    def from_json(self, json_object, host_instrument):
        # PlaybackImplementations implement a version of from_json that requires us to pass the host instrument
        # this avoids the circularity of the host instrument containing references to the playback implementations
        # and the playback implementations containing a reference to the host_instrument
        pass


class _MIDIPlaybackImplementation(PlaybackImplementation, ABC):

    def __init__(self, host_instrument, num_channels=8):
        super().__init__(host_instrument)
        self.num_channels = num_channels
        self.ringing_notes = []

    # -------------------------- Abstract methods to be implemented by subclasses--------------

    @abstractmethod
    def note_on(self, chan, pitch, velocity_from_0_to_1):
        pass

    @abstractmethod
    def note_off(self, chan, pitch):
        pass

    @abstractmethod
    def pitch_bend(self, chan, bend_in_semitones):
        pass

    @abstractmethod
    def set_max_pitch_bend(self, max_bend_in_semitones):
        pass

    @abstractmethod
    def expression(self, chan, expression_from_0_to_1):
        pass

    # -------------------------------- Main Playback Methods --------------------------------

    def start_note(self, note_id, pitch, volume, properties, other_parameter_values: dict = None):
        this_note_info = self.note_info_dict[note_id]
        this_note_fixed = "fixed" in this_note_info["flags"]
        int_pitch = int(round(pitch))

        # make a list of available channels to add this note to, ones that won't cause pitch bend / expression conflicts
        available_channels = list(range(self.num_channels))
        oldest_note_id = None

        # go through all currently active notes
        for other_note_id, other_note_info in self.note_info_dict.items():
            # check to see that this other note has been handled by this playback implementation (for instance, a silent
            # note will be skipped, since it was never passed to the playback implementations). Also check that it
            # hasn't been prematurely ended.
            if self in other_note_info and not other_note_info[self]["prematurely_ended"]:
                other_note_channel = other_note_info[self]["channel"]
                other_note_fixed = "fixed" in other_note_info["flags"]
                other_note_pitch = other_note_info["parameter_values"]["pitch"]
                other_note_int_pitch = other_note_info[self]["midi_note"]
                # this new note only share a midi channel with the old note if:
                #   1) both notes are fixed (i.e. will not do a pitch or expression change, which is channel-wide)
                #   2) the notes are not on the same midi key (since that will make a note off in one affect the other)
                #   3) the notes don't have conflicting microtonality (i.e. one or both need a pitch bend, and it's
                # not the exact same pitch bend.)
                conflicting_microtonality = (pitch != int_pitch or other_note_pitch != other_note_int_pitch) and \
                                            (round(pitch - int_pitch, 5) !=  # round to fix float error
                                             round(other_note_pitch - other_note_int_pitch, 5))
                channel_compatible = this_note_fixed and other_note_fixed \
                                     and int_pitch != other_note_int_pitch and not conflicting_microtonality
                if not channel_compatible:
                    if other_note_channel in available_channels:
                        available_channels.remove(other_note_channel)
                    # keep track of the oldest note that's holding onto a channel
                    if oldest_note_id is None or other_note_id < oldest_note_id:
                        oldest_note_id = other_note_id

        # go through all ringing notes, and remove those channels if not compatible
        # this means a note that has ended, which was microtonal, and which may still be ringing
        for ringing_channel, ringing_midi_note, ringing_pitch in self.ringing_notes:
            conflicting_microtonality = (pitch != int_pitch or ringing_midi_note != ringing_pitch) and \
                                        (round(pitch - int_pitch, 5) !=  # round to fix float error
                                         round(ringing_pitch - ringing_midi_note, 5))
            # Note that here, unlike above, there's no need to check if the other note is fixed, since it's done
            # and just ringing. Also, it's okay if the other note is of the same pitch, since the note_off message
            # has already been sent.
            channel_compatible = this_note_fixed and not conflicting_microtonality
            if not channel_compatible and ringing_channel in available_channels:
                available_channels.remove(ringing_channel)

        # pick the first free channel, or free one up if there are no free channels
        if len(available_channels) > 0:
            # if there's a free channel, return the lowest number available
            channel = available_channels[0]
        elif len(self.ringing_notes) > 0:
            # if there are any channels we avoided because they have ringing microtonal pitches, we turn to those first
            channel, _, _ = self.ringing_notes.pop(0)
            # also, need to make sure to zero-out the pitch bend and reset expression. (This would happen at the end
            # of "delete_after_pause" below, but we need the channel to be ready to go early.)
            self.pitch_bend(channel, 0)
            self.expression(channel, 1)
        else:
            # otherwise, we'll have to kill an old note to find a free channel
            # get the info we stored on this note, related to this specific playback implementation
            # (see end of start_note method for explanation)
            oldest_note_info = self.note_info_dict[oldest_note_id][self]
            self.note_off(oldest_note_info["channel"], oldest_note_info["midi_note"])
            # reset the pitch bend on that channel
            self.pitch_bend(oldest_note_info["channel"], 0)
            self.expression(oldest_note_info["channel"], 1)
            # flag it as prematurely ended so that we send no further midi commands
            oldest_note_info["prematurely_ended"] = True
            # if every channel is playing this pitch, we will end the oldest note so we can
            channel = oldest_note_info["channel"]

        # start the note on that channel
        # note that we start it at the max volume that it wil lever reach, and use expression to get to the start volume
        self.note_on(channel, int_pitch, this_note_info["max_volume"])
        if pitch != int_pitch:
            self.pitch_bend(channel, pitch - int_pitch)
        else:
            self.pitch_bend(channel, 0)
        self.expression(channel, volume / this_note_info["max_volume"] if this_note_info["max_volume"] > 0 else 0)
        # store the midi note that we pressed for this note, the channel we pressed it on, and make an entry (initially
        # false) for whether or not we ended this note prematurely (to free up a channel for a newer note).
        # Note that we're creating here a dictionary within the note_info dictionary, using this PlaybackImplementation
        # instance as the key. This way, there can never be conflict between data stored by this PlaybackImplementation
        # and data stored by other PlaybackImplementations
        this_note_info[self] = {
            "midi_note": int_pitch,
            "channel": channel,
            "prematurely_ended": False
        }

    def end_note(self, note_id):
        this_note_info = self.note_info_dict[note_id]
        assert self in this_note_info, "Note was never started by the SoundfontPlaybackImplementer; this is bad."
        this_note_implementation_info = this_note_info[self]
        if not this_note_implementation_info["prematurely_ended"]:
            self.note_off(this_note_implementation_info["channel"], this_note_implementation_info["midi_note"])
            ringing_note_info = (this_note_implementation_info["channel"], this_note_implementation_info["midi_note"],
                                 this_note_info["parameter_values"]["pitch"])

            # we need to consider this note as potentially still ringing for some period
            # after it finished. We don't want to  accidentally pitch-shift the release trail
            self.ringing_notes.append(ringing_note_info)

            def delete_after_pause():
                time.sleep(0.5)
                if ringing_note_info in self.ringing_notes:
                    self.ringing_notes.remove(ringing_note_info)
                    self.pitch_bend(ringing_note_info[0], 0)
                    self.expression(ringing_note_info[0], 1)

            fork_unsynchronized(delete_after_pause)

    def change_note_pitch(self, note_id, new_pitch):
        if note_id not in self.note_info_dict:
            # theoretically could happen if the end_note call happens right before this is called in the
            # asynchronous animation function. We don't want to cause a KeyError, so this avoids that possibility
            return
        this_note_info = self.note_info_dict[note_id]
        assert self in this_note_info, "Note was never started by the SoundfontPlaybackImplementer; this is bad."
        this_note_implementation_info = this_note_info[self]
        if not this_note_implementation_info["prematurely_ended"]:
            self.pitch_bend(this_note_implementation_info["channel"],
                            new_pitch - this_note_implementation_info["midi_note"])

    def change_note_volume(self, note_id, new_volume):
        if note_id not in self.note_info_dict:
            # theoretically could happen if the end_note call happens right before this is called in the
            # asynchronous animation function. We don't want to cause a KeyError, so this avoids that possibility
            return
        this_note_info = self.note_info_dict[note_id]
        assert self in this_note_info, "Note was never started by the SoundfontPlaybackImplementer; this is bad."
        this_note_implementation_info = this_note_info[self]
        if not this_note_implementation_info["prematurely_ended"]:
            self.expression(this_note_implementation_info["channel"], new_volume / this_note_info["max_volume"])

    def change_note_parameter(self, note_id, parameter_name, new_value):
        # parameter changes are not implemented for MidiPlaybackImplementations
        # perhaps they could be for some other uses, maybe program changes?
        pass


class SoundfontPlaybackImplementation(_MIDIPlaybackImplementation):

    def __init__(self, host_instrument, bank_and_preset=(0, 0), soundfont="default",
                 num_channels=8, audio_driver="default", max_pitch_bend="default"):
        super().__init__(host_instrument, num_channels)

        # we hold onto these arguments for the purposes of json serialization
        # note that if the audio_driver said "default", then we save it as "default",
        # rather than what that default resolved to.
        self.num_channels = num_channels
        self.audio_driver = audio_driver

        audio_driver = playback_settings.default_audio_driver if audio_driver == "default" else audio_driver
        self.soundfont = playback_settings.default_soundfont if soundfont == "default" else soundfont
        soundfont_host_resource_key = "{}_soundfont_host".format(audio_driver)
        if not self.has_shared_resource(soundfont_host_resource_key):
            self.set_shared_resource(soundfont_host_resource_key, SoundfontHost(self.soundfont, audio_driver))
        self.soundfont_host = self.get_shared_resource(soundfont_host_resource_key)
        if self.soundfont not in self.soundfont_host.soundfont_ids:
            self.soundfont_host.load_soundfont(self.soundfont)
        self.soundfont_instrument = self.soundfont_host.add_instrument(num_channels, bank_and_preset, self.soundfont)

        self.bank_and_preset = bank_and_preset
        self.max_pitch_bend = None
        self.set_max_pitch_bend(playback_settings.default_max_soundfont_pitch_bend
                                if max_pitch_bend == "default" else max_pitch_bend)

    # -------------------------------- Main Playback Methods --------------------------------

    def note_on(self, chan, pitch, velocity_from_0_to_1):
        self.soundfont_instrument.note_on(chan, pitch, velocity_from_0_to_1)

    def note_off(self, chan, pitch):
        self.soundfont_instrument.note_off(chan, pitch)

    def pitch_bend(self, chan, bend_in_semitones):
        self.soundfont_instrument.pitch_bend(chan, bend_in_semitones)

    def set_max_pitch_bend(self, semitones):
        self.soundfont_instrument.set_max_pitch_bend(semitones)
        self.max_pitch_bend = semitones

    def expression(self, chan, expression_from_0_to_1):
        self.soundfont_instrument.expression(chan, expression_from_0_to_1)

    def to_json(self):
        return {
            "type": "SoundfontPlaybackImplementation",
            "args": {
                "bank_and_preset": self.bank_and_preset,
                "soundfont": self.soundfont,
                "num_channels": self.num_channels,
                "audio_driver": self.audio_driver,
                "max_pitch_bend": self.max_pitch_bend
            }
        }

    @classmethod
    def from_json(cls, json_object, host_instrument):
        return cls(host_instrument, **json_object["args"])


class MIDIStreamPlaybackImplementation(_MIDIPlaybackImplementation):

    def __init__(self, host_instrument, midi_output_device="default", num_channels=8,
                 midi_output_name=None, max_pitch_bend="default"):
        super().__init__(host_instrument)

        # we hold onto these arguments for the purposes of json serialization
        # note that if the midi_output_device or midi_output_name said "default",
        # then we save it as "default", rather than what that default resolved to.
        self.num_channels = num_channels
        self.midi_output_device = midi_output_device
        self.midi_output_name = midi_output_name

        midi_output_device = playback_settings.default_midi_output_device if midi_output_device == "default" \
            else midi_output_device
        if midi_output_name is None:
            # if no midi output name is given, fall back to the instrument name
            # if the instrument has no name, fall back to "Unnamed"
            midi_output_name = "Unnamed" if host_instrument.name is None else host_instrument.name

        # since rtmidi can only have 16 output channels, we need to create several output devices if we are using more
        if num_channels <= 16:
            self.rt_simple_outs = [SimpleRtMidiOut(midi_output_device, midi_output_name)]
        else:
            self.rt_simple_outs = [
                SimpleRtMidiOut(midi_output_device, midi_output_name + " chans {}-{}".format(chan, chan + 15))
                for chan in range(0, num_channels, 16)
            ]

        self.max_pitch_bend = None
        self.set_max_pitch_bend(playback_settings.default_max_streaming_midi_pitch_bend
                                if max_pitch_bend == "default" else max_pitch_bend)

    def get_rt_simple_out_and_channel(self, chan):
        assert chan < self.num_channels
        adjusted_chan = chan % 16
        rt_simple_out = self.rt_simple_outs[(chan - adjusted_chan) // 16]
        return rt_simple_out, adjusted_chan

    def note_on(self, chan, pitch, velocity_from_0_to_1):
        # unless it's the standard value of two semitones, reinforce the max pitch bend at the start of every note,
        # since we may start recording partway through
        if self.max_pitch_bend != 2:
            self.set_max_pitch_bend(self.max_pitch_bend)
        rt_simple_out, chan = self.get_rt_simple_out_and_channel(chan)
        velocity = max(0, min(127, int(velocity_from_0_to_1 * 127)))
        rt_simple_out.note_on(chan, pitch, velocity)

    def note_off(self, chan, pitch):
        rt_simple_out, chan = self.get_rt_simple_out_and_channel(chan)
        rt_simple_out.note_off(chan, pitch)

    def pitch_bend(self, chan, bend_in_semitones):
        rt_simple_out, chan = self.get_rt_simple_out_and_channel(chan)
        directional_bend_value = int(bend_in_semitones / self.max_pitch_bend * 8192)

        if directional_bend_value > 8192 or directional_bend_value < -8192:
            logging.warning("Attempted pitch bend beyond maximum range (default is 2 semitones). Call set_max_"
                            "pitch_bend on your MidiScampInstrument to expand the range.")
        # we can't have a directional pitch bend popping up to 8192, because we'll go one above the max allowed
        # on the other hand, -8192 is fine, since that will add up to zero
        # However, notice above that we don't send a warning about going beyond max pitch bend for a value of exactly
        # 8192, since that's obnoxious and confusing. Better to just quietly clip it to 8191
        directional_bend_value = max(-8192, min(directional_bend_value, 8191))
        rt_simple_out.pitch_bend(chan, directional_bend_value + 8192)

    def set_max_pitch_bend(self, max_bend_in_semitones: int):
        """
        Sets the maximum pitch bend to the given number of semitones up and down for all tracks associated
        with this instrument. Note that this will often be ignored by midi receivers.
        """
        if max_bend_in_semitones != int(max_bend_in_semitones):
            logging.warning("Max pitch bend must be an integer number of semitones. "
                            "The value of {} is being rounded up.".format(max_bend_in_semitones))
            max_bend_in_semitones = int(max_bend_in_semitones) + 1

        for chan in range(self.num_channels):
            rt_simple_out, chan = self.get_rt_simple_out_and_channel(chan)
            rt_simple_out.cc(chan, 101, 0)
            rt_simple_out.cc(chan, 100, 0)
            rt_simple_out.cc(chan, 6, max_bend_in_semitones)
            rt_simple_out.cc(chan, 100, 127)

        self.max_pitch_bend = max_bend_in_semitones

    def expression(self, chan, expression_from_0_to_1):
        rt_simple_out, chan = self.get_rt_simple_out_and_channel(chan)
        expression_val = max(0, min(127, int(expression_from_0_to_1 * 127)))
        rt_simple_out.expression(chan, expression_val)

    def to_json(self):
        return {
            "type": "MIDIStreamPlaybackImplementation",
            "args": {
                "midi_output_device": self.midi_output_device,
                "num_channels": self.num_channels,
                "midi_output_name": self.midi_output_name,
                "max_pitch_bend": self.max_pitch_bend
            }
        }

    @classmethod
    def from_json(cls, json_object, host_instrument):
        return cls(host_instrument, **json_object["args"])


class OSCPlaybackImplementation(PlaybackImplementation):

    def __init__(self, host_instrument, port, ip_address="127.0.0.1", message_prefix=None,
                 osc_message_addresses="default"):
        super().__init__(host_instrument)
        # the output client for OSC messages
        # by default the IP address is the local 127.0.0.1
        self.ip_address = ip_address
        self.port = port

        self.client = udp_client.SimpleUDPClient(ip_address, port)
        # the first part of the osc message; used to distinguish between instruments
        # by default uses the name of the instrument with spaces removed
        self.message_prefix = message_prefix if message_prefix is not None \
            else (self.host_instrument.name.replace(" ", "") if self.host_instrument.name is not None else "unnamed")

        self.osc_message_addresses = playback_settings.osc_message_addresses
        if osc_message_addresses != "default":
            assert isinstance(osc_message_addresses, dict), "osc_message_addresses argument must be a complete or " \
                                                            "incomplete dictionary of alternate osc messages"
            # for each type of osc message, use the one specified in the osc_message_addresses argument if available,
            # falling back to the one in playback_settings if it's not available
            self.osc_message_addresses = {key: osc_message_addresses[key] if key in osc_message_addresses else value
                                          for key, value in playback_settings.osc_message_addresses.items()}

        self._currently_playing = []

        def clean_up():
            for note_id in list(self._currently_playing):
                self.end_note(note_id)

        atexit.register(clean_up)

    def start_note(self, note_id, pitch, volume, properties, other_parameter_values: dict = None):
        self.client.send_message("/{}/{}".format(self.message_prefix, self.osc_message_addresses["start_note"]),
                                 [note_id, pitch, volume])
        self._currently_playing.append(note_id)
        for param, value in other_parameter_values.items():
            self.change_note_parameter(note_id, param, value)

    def end_note(self, note_id):
        self.client.send_message("/{}/{}".format(self.message_prefix, self.osc_message_addresses["end_note"]), [note_id])
        if note_id in self._currently_playing:
            self._currently_playing.remove(note_id)

    def change_note_pitch(self, note_id, new_pitch):
        self.client.send_message("/{}/{}".format(self.message_prefix, self.osc_message_addresses["change_pitch"]),
                                 [note_id, new_pitch])

    def change_note_volume(self, note_id, new_volume):
        self.client.send_message("/{}/{}".format(self.message_prefix, self.osc_message_addresses["change_volume"]),
                                 [note_id, new_volume])

    def change_note_parameter(self, note_id, parameter_name, new_value):
        self.client.send_message("/{}/{}/{}".format(
            self.message_prefix, self.osc_message_addresses["change_parameter"], parameter_name), [note_id, new_value])

    def set_max_pitch_bend(self, semitones):
        pass

    def to_json(self):
        return {
            "type": "OSCPlaybackImplementation",
            "args": {
                "port": self.port,
                "ip_address": self.ip_address,
                "message_prefix": self.message_prefix,
                "osc_message_addresses": self.osc_message_addresses
            }
        }

    @classmethod
    def from_json(cls, json_object, host_instrument):
        return cls(host_instrument, **json_object["args"])
