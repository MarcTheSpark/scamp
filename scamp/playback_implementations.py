"""
Module containing the abstract base class :class:`PlaybackImplementation`, as well as several of its concrete
subclasses: :class:`SoundfontPlaybackImplementation`, :class:`MidiPlaybackImplementations`, and
:class:`OSCPlaybackImplementation`. :class:`PlaybackImplementations` do the actual work of playback, either by
playing sounds or by sending messages to external synthesizers to play sounds.
A :class:`~scamp.instruments.ScampInstrument` can have one or more :class:`PlaybackImplementations`.
"""

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

from ._midi import SimpleRtMidiOut, MIDIChannelManager, NoFreeChannelError
from ._soundfont_host import SoundfontHost
from .note_properties import NoteProperties
from abc import abstractmethod
from ._dependencies import pythonosc
from typing import Tuple, Optional
import logging
from .settings import playback_settings
from .utilities import SavesToJSON, resolve_path
import math


class PlaybackImplementation(SavesToJSON):

    """
    Abstract base class for playback implementations, which do the actual work of playback, either by playing sounds or
    by sending messages to external synthesizers to play sounds.
    """

    @abstractmethod
    def start_note(self, note_id: int, pitch: float, volume: float, properties: NoteProperties,
                   note_info_dict: dict) -> None:
        """
        Method that implements the start of a note

        :param note_id: unique identifier for the note we are starting
        :param pitch: floating-point MIDI pitch value
        :param volume: floating-point volume value (from 0 to 1)
        :param properties: a NotePropertiesDictionary
        :param other_parameter_values: dictionary mapping parameter name to parameter value for parameters other than
            pitch and volume. (This information was extracted from the properties dictionary.)
        :param note_info_dict: dictionary with auxiliary info about this note (e.g. the clock it's running on,
            time stamp, various flags)
        """
        pass

    @abstractmethod
    def end_note(self, note_id: int) -> None:
        """
        Method that implements the end of a note

        :param note_id: unique identifier of the note to end
        """
        pass

    @abstractmethod
    def change_note_pitch(self, note_id: int, new_pitch: float) -> None:
        """
        Method that implements the change of a note's pitch

        :param note_id: unique identifier of the note whose pitch to change
        :param new_pitch: new (floating-point) MIDI pitch value
        """
        pass

    @abstractmethod
    def change_note_volume(self, note_id: int, new_volume: float) -> None:
        """
        Method that implements the change of a note's volume

        :param note_id: unique identifier of the note whose volume to change
        :param new_volume: new floating point volume value from 0 to 1
        """
        pass

    @abstractmethod
    def change_note_parameter(self, note_id: int, parameter_name: str, new_value: float) -> None:
        """
        Method that implements the change of a parameter other than pitch or volume

        :param note_id: unique identifier of the note to effect
        :param parameter_name: name of the parameter to change
        :param new_value: new floating-point value of that parameter
        """
        pass

    @abstractmethod
    def set_max_pitch_bend(self, semitones: int) -> None:
        """
        Method that sets the max pitch bend for MIDI-based playback implementations
        This is only relevant when playback is happening via the MIDI protocol.

        :param semitones: unique identifier of the note to effect
        """
        pass


class _MIDIPlaybackImplementation(PlaybackImplementation):

    """
    This is the abstract base class for playback implementations that use the MIDI protocol.
    It handles all of the channel management nonsense so that that pitch bends don't conflict with
    one another, and that kind of thing, exposing the more basic note_on/note_off abstract methods
    to be overridden.

    :param num_channels: how many MIDI channels to use for this instrument. Where channel-wide messages (such as
        pitch-bend messages) are involved, it is essential to have several channels at our disposal.
    :param note_on_and_off_only: This enforces a rule of no dynamic pitch bends, expression (volume) changes, or other
        cc messages. Valuable when using :code:`start_note` instead of :code:`play_note` in music that doesn't do any
        dynamic pitch/volume/parameter changes. Without this flag, notes will all be placed on separate MIDI channels,
        since they could potentially change pitch or volume; with this flags, we know they won't, so they can share
        the same MIDI channels, only using an extra one due to microtonality.
    """

    def __init__(self, num_channels: int = 8, note_on_and_off_only: bool = False):
        super().__init__()
        self.note_on_and_off_only = note_on_and_off_only
        self.num_channels = num_channels
        self.midi_channel_manager = MIDIChannelManager(num_channels)
        self._note_info = {}

    # -------------------------- Abstract methods to be implemented by subclasses--------------

    @abstractmethod
    def note_on(self, chan: int, pitch: int, velocity_from_0_to_1: float) -> None:
        """
        Sends a note_on MIDI message

        :param chan: channel to send message on
        :param pitch: integer MIDI pitch value
        :param velocity_from_0_to_1: velocity to send (NB: scaled from 0 to 1)
        """
        pass

    @abstractmethod
    def note_off(self, chan: int, pitch: int) -> None:
        """
        Sends a note_off MIDI message

        :param chan: channel to send message on
        :param pitch: integer MIDI pitch value
        """
        pass

    @abstractmethod
    def pitch_bend(self, chan: int, bend_in_semitones: float) -> None:
        """
        Sends a MIDI pitch bend message

        :param chan: channel to send message on
        :param bend_in_semitones: the pitch bend amount (in semitones!)
        """
        pass

    @abstractmethod
    def set_max_pitch_bend(self, max_bend_in_semitones: int) -> None:
        """
        Sets the max pitch bend for this MIDI device

        :param max_bend_in_semitones: value to set as maximum pitch bend
        """
        pass

    @abstractmethod
    def expression(self, chan, expression_from_0_to_1) -> None:
        """
        Sends a midi expression message

        :param chan: channel to send message on
        :param expression_from_0_to_1: expression to send (NB: scaled from 0 to 1)
        :return:
        """
        pass

    @abstractmethod
    def cc(self, chan: int, cc_number: int, value_from_0_to_1: float) -> None:
        """
        Sends an arbitrary midi CC message

        :param chan: channel to send the message on
        :param cc_number: number representing the type of the control change message
        :param value_from_0_to_1: value to send (NB: scaled from 0 to 1)
        """
        pass

    # -------------------------------- Main Playback Methods --------------------------------

    def start_note(self, note_id, pitch, volume, properties, note_info_dict):
        # the note info dictionary was passed along via properties.temp
        # store it under the note id number in the _note_info_dict
        this_note_info = note_info_dict

        this_note_fixed = "fixed" in this_note_info["flags"] or self.note_on_and_off_only
        if this_note_fixed:
            this_note_info["max_volume"] = volume

        # this insures that we always round down when at the 0.5 mark. Otherwise, python sometimes rounds up and
        # sometimes rounds down, which needlessly puts notes on different channels
        int_pitch = int(pitch) if pitch % 1 <= 0.5 else math.ceil(pitch)
        pitch_bend = round(pitch - int_pitch, 10)
        cc_values = properties.get_midi_cc_start_values()

        try:
            chan = self.midi_channel_manager.assign_note_to_channel(
                note_id, int_pitch, pitch_bend if this_note_fixed else "variable",
                cc_values if this_note_fixed else "variable"
            )
        except NoFreeChannelError as e:
            channel_to_free = e.best_channel_to_free
            for note in e.notes_to_free:
                self.note_off(channel_to_free, note.pitch)
                self.midi_channel_manager.end_note(note.note_id)
                self._note_info[note.note_id]["prematurely_ended"] = True
            chan = self.midi_channel_manager.assign_note_to_channel(
                note_id, int_pitch, pitch_bend if this_note_fixed else "variable",
                cc_values if this_note_fixed else "variable"
            )

        self.pitch_bend(chan, pitch_bend)

        if not self.note_on_and_off_only:
            # start it at the max volume that it will ever reach, and use expression to get to the start volume
            self.expression(chan, volume / this_note_info["max_volume"] if this_note_info["max_volume"] > 0 else 0)
            for cc_num, cc_value in cc_values.items():
                self.cc(chan, cc_num, cc_value)

        self.note_on(chan, int_pitch, this_note_info["max_volume"])

        self._note_info[note_id] = {
            "midi_note": int_pitch,
            "velocity": this_note_info["max_volume"],
            "channel": chan,
            "prematurely_ended": False
        }

    def end_note(self, note_id):
        this_note_info = self._note_info[note_id]
        if not this_note_info["prematurely_ended"]:
            self.note_off(this_note_info["channel"], this_note_info["midi_note"])
            self.midi_channel_manager.end_note(note_id)

    def change_note_pitch(self, note_id, new_pitch):
        if self.note_on_and_off_only:
            raise RuntimeError(f"Change of pitch being called on with the `note_on_and_off_only` flag set")
        if note_id in self._note_info:  # make sure the note is active
            this_note_info = self._note_info[note_id]
            if not this_note_info["prematurely_ended"]:
                self.pitch_bend(this_note_info["channel"], new_pitch - this_note_info["midi_note"])

    def change_note_volume(self, note_id, new_volume):
        if self.note_on_and_off_only:
            raise RuntimeError(f"Change of pitch being called on with the `note_on_and_off_only` flag set")
        if note_id in self._note_info:  # make sure the note is active
            this_note_info = self._note_info[note_id]
            if not this_note_info["prematurely_ended"]:
                self.expression(this_note_info["channel"], new_volume / this_note_info["velocity"])

    def change_note_parameter(self, note_id, parameter_name, new_value):
        if self.note_on_and_off_only:
            raise RuntimeError(f"Change of pitch being called on with the `note_on_and_off_only` flag set")
        if note_id in self._note_info:  # make sure the note is active
            this_note_info = self._note_info[note_id]
            if not this_note_info["prematurely_ended"] and parameter_name.isdigit() and 0 <= int(parameter_name) < 128:
                cc_number = int(parameter_name)
                self.cc(this_note_info["channel"], cc_number, new_value)


class SoundfontPlaybackImplementation(_MIDIPlaybackImplementation):

    """
    Playback implementation that does Soundfont playback, via the MIDI protocol.

    :param bank_and_preset: The bank and preset within the given soundfont to use for playback
    :param soundfont: String representing the soundfont to use for playback. Defaults to the one defined in
        playback_settings.default_soundfont
    :param num_channels: How many MIDI channels to use for this instrument. Where channel-wide messages (such as
        pitch-bend messages) are involved, it is essential to have several channels at our disposal.
    :param audio_driver: name of the audio_driver to use. Defaults to the one defined in
        playback_settings.default_audio_driver
    :param max_pitch_bend: max pitch bend allowed on this instrument. Defaults to the one defined in
        playback_settings.default_max_soundfont_pitch_bend.
    :param note_on_and_off_only: This enforces a rule of no dynamic pitch bends, expression (volume) changes, or other
        cc messages. Valuable when using :code:`start_note` instead of :code:`play_note` in music that doesn't do any
        dynamic pitch/volume/parameter changes. Without this flag, notes will all be placed on separate MIDI channels,
        since they could potentially change pitch or volume; with this flags, we know they won't, so they can share
        the same MIDI channels, only using an extra one due to microtonality.
    """

    soundfont_hosts = {}

    def __init__(self, bank_and_preset: Tuple[int, int] = (0, 0), soundfont: str = "default", num_channels: int = 8,
                 audio_driver: str = "default", max_pitch_bend: int = "default", note_on_and_off_only: bool = False):
        super().__init__(num_channels, note_on_and_off_only)

        # we hold onto these arguments for the purposes of json serialization
        # note that if the audio_driver said "default", then we save it as "default",
        # rather than what that default resolved to.
        self.audio_driver = audio_driver
        self.bank_and_preset = bank_and_preset

        self.max_pitch_bend = max_pitch_bend
        self.soundfont = playback_settings.default_soundfont if soundfont == "default" else soundfont

        # The soundfont host is shared between all instances of SoundfontPlaybackImplementation sharing the same
        # audio driver. (Theoretically, if you created two SoundfontPlaybackImplementations using different drivers
        # we would have to create different underlying SoundfontHosts, so the SoundfontHost is stored in a dictionary
        # indexed by audio driver.) We create it if needed.
        audio_driver = playback_settings.default_audio_driver if self.audio_driver == "default" else self.audio_driver
        if audio_driver in SoundfontPlaybackImplementation.soundfont_hosts:
            self.soundfont_host = SoundfontPlaybackImplementation.soundfont_hosts[audio_driver]
        else:
            self.soundfont_host = SoundfontPlaybackImplementation.soundfont_hosts[audio_driver] = \
                SoundfontHost(
                    self.soundfont, audio_driver,
                    recording_file_path=resolve_path(playback_settings.recording_file_path)
                    if playback_settings.recording_file_path is not None else None,
                    recording_time_range=(float(playback_settings.recording_time_range[0]),
                                          float(playback_settings.recording_time_range[1]))
                )
        if self.soundfont not in self.soundfont_host.soundfont_ids:
            self.soundfont_host.load_soundfont(self.soundfont)
        self.soundfont_instrument = self.soundfont_host.add_instrument(self.num_channels, self.bank_and_preset,
                                                                       self.soundfont)
        self.set_max_pitch_bend(playback_settings.default_max_soundfont_pitch_bend
                                if self.max_pitch_bend == "default" else self.max_pitch_bend)

    # -------------------------------- Main Playback Methods --------------------------------

    def note_on(self, chan: int, pitch: int, velocity_from_0_to_1: float):
        self.soundfont_instrument.note_on(chan, pitch, velocity_from_0_to_1)

    def note_off(self, chan: int, pitch: int):
        self.soundfont_instrument.note_off(chan, pitch)

    def pitch_bend(self, chan: int, bend_in_semitones: float):
        self.soundfont_instrument.pitch_bend(chan, bend_in_semitones)

    def set_max_pitch_bend(self, semitones: int):
        self.soundfont_instrument.set_max_pitch_bend(semitones)
        self.max_pitch_bend = semitones

    def expression(self, chan: int, expression_from_0_to_1: float):
        self.soundfont_instrument.cc(chan, 11, expression_from_0_to_1)

    def cc(self, chan: int, cc_number: int, value_from_0_to_1: float):
        self.soundfont_instrument.cc(chan, cc_number, value_from_0_to_1)

    def _to_dict(self):
        return {
            "bank_and_preset": self.bank_and_preset,
            "soundfont": self.soundfont,
            "num_channels": self.num_channels,
            "audio_driver": self.audio_driver,
            "max_pitch_bend": self.max_pitch_bend
        }

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)


class MIDIStreamPlaybackImplementation(_MIDIPlaybackImplementation):
    """
    Playback implementation that sends an outgoing MIDI stream to an external synthesizer / program

    :param midi_output_device: name or port number of the midi output device to use.
    :param num_channels: How many MIDI channels to use for this instrument. Where channel-wide messages (such as
        pitch-bend messages) are involved, it is essential to have several channels at our disposal.
    :param midi_output_name: name to use when sending messages
    :param max_pitch_bend: max pitch bend allowed on this instrument. Defaults to the one defined in
        playback_settings.default_max_streaming_midi_pitch_bend.
    :param note_on_and_off_only: This enforces a rule of no dynamic pitch bends, expression (volume) changes, or other
        cc messages. Valuable when using :code:`start_note` instead of :code:`play_note` in music that doesn't do any
        dynamic pitch/volume/parameter changes. Without this flag, notes will all be placed on separate MIDI channels,
        since they could potentially change pitch or volume; with this flags, we know they won't, so they can share
        the same MIDI channels, only using an extra one due to microtonality.
    """

    def __init__(self, midi_output_device: str = "default", num_channels=8, midi_output_name: Optional[str] = None,
                 max_pitch_bend: int = "default", note_on_and_off_only: bool = False, start_channel=0):
        super().__init__(num_channels, note_on_and_off_only)

        # we hold onto these arguments for the purposes of json serialization
        # note that if the midi_output_device or midi_output_name said "default",
        # then we save it as "default", rather than what that default resolved to.
        self.start_channel = start_channel
        self.num_channels = num_channels
        self.midi_output_device = midi_output_device
        self.midi_output_name = midi_output_name

        midi_output_name = "SCAMP" if midi_output_name is None else midi_output_name

        # since rtmidi can only have 16 output channels, we need to create several output devices if we are using more
        if start_channel + num_channels <= 16:
            self.rt_simple_outs = [SimpleRtMidiOut(midi_output_device, midi_output_name)]
        else:
            self.rt_simple_outs = [
                SimpleRtMidiOut(midi_output_device, midi_output_name + " chans {}-{}".format(chan, chan + 15))
                for chan in range(0, start_channel + num_channels, 16)
            ]

        self.max_pitch_bend = None
        self.set_max_pitch_bend(playback_settings.default_max_streaming_midi_pitch_bend
                                if max_pitch_bend == "default" else max_pitch_bend)

    def _get_rt_simple_out_and_channel(self, chan):
        assert chan < self.num_channels
        adjusted_chan = (chan + self.start_channel) % 16
        rt_simple_out = self.rt_simple_outs[chan // 16]
        return rt_simple_out, adjusted_chan

    def note_on(self, chan: int, pitch: int, velocity_from_0_to_1: float):
        # unless it's the standard value of two semitones, reinforce the max pitch bend at the start of every note,
        # since we may start recording partway through
        if self.max_pitch_bend != 2:
            self.set_max_pitch_bend(self.max_pitch_bend)
        rt_simple_out, chan = self._get_rt_simple_out_and_channel(chan)
        velocity = int(playback_settings.streaming_midi_volume_to_velocity_curve.value_at(velocity_from_0_to_1))
        rt_simple_out.note_on(chan, pitch, velocity)

    def note_off(self, chan: int, pitch: int):
        rt_simple_out, chan = self._get_rt_simple_out_and_channel(chan)
        rt_simple_out.note_off(chan, pitch)

    def pitch_bend(self, chan: int, bend_in_semitones: float):
        rt_simple_out, chan = self._get_rt_simple_out_and_channel(chan)
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
        if max_bend_in_semitones != int(max_bend_in_semitones):
            logging.warning("Max pitch bend must be an integer number of semitones. "
                            "The value of {} is being rounded up.".format(max_bend_in_semitones))
            max_bend_in_semitones = int(max_bend_in_semitones) + 1

        for chan in range(self.num_channels):
            rt_simple_out, chan = self._get_rt_simple_out_and_channel(chan)
            rt_simple_out.cc(chan, 101, 0)
            rt_simple_out.cc(chan, 100, 0)
            rt_simple_out.cc(chan, 6, max_bend_in_semitones)
            rt_simple_out.cc(chan, 100, 127)

        self.max_pitch_bend = max_bend_in_semitones

    def expression(self, chan: int, expression_from_0_to_1: float):
        self.cc(chan, 11, expression_from_0_to_1)

    def cc(self, chan: int, cc_number: int, value_from_0_to_1: float):
        rt_simple_out, chan = self._get_rt_simple_out_and_channel(chan)
        cc_value = max(0, min(127, int(value_from_0_to_1 * 127)))
        rt_simple_out.cc(chan, cc_number, cc_value)

    def _to_dict(self):
        return {
            "midi_output_device": self.midi_output_device,
            "num_channels": self.num_channels,
            "midi_output_name": self.midi_output_name,
            "max_pitch_bend": self.max_pitch_bend
        }

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)


class OSCPlaybackImplementation(PlaybackImplementation):
    """
    Playback implementation that sends outgoing OSC messages to an external synthesizer / program

    :param port: OSC port to use for playback
    :param ip_address: ip_address to send OSC messages to
    :param message_prefix: prefix used in the address of all messages sent. Defaults to the name of the instrument
    :param osc_message_addresses: dictionary mapping the kind of the message to the address for that message. Defaults
         to playback_settings.osc_message_addresses
    """

    def __init__(self, port: int, ip_address: str = "127.0.0.1", message_prefix: str = "scamp",
                 osc_message_addresses: dict = "default"):
        super().__init__()
        # the output client for OSC messages
        # by default the IP address is the local 127.0.0.1
        self.ip_address = ip_address
        self.port = port

        self.client = pythonosc.udp_client.SimpleUDPClient(ip_address, port)
        # the first part of the osc message; used to distinguish between instruments
        # by default uses the name of the instrument with spaces removed
        self.message_prefix = message_prefix

        self.osc_message_addresses = playback_settings.osc_message_addresses
        if osc_message_addresses != "default":
            assert isinstance(osc_message_addresses, dict), "osc_message_addresses argument must be a complete or " \
                                                            "incomplete dictionary of alternate osc messages"
            # for each type of osc message, use the one specified in the osc_message_addresses argument if available,
            # falling back to the one in playback_settings if it's not available
            self.osc_message_addresses = {key: osc_message_addresses[key] if key in osc_message_addresses else value
                                          for key, value in playback_settings.osc_message_addresses.items()}

        self._currently_playing = []

    def start_note(self, note_id: int, pitch: float, volume: float, properties: NoteProperties,
                   note_info_dict: dict) -> None:
        self.client.send_message("/{}/{}".format(self.message_prefix, self.osc_message_addresses["start_note"]),
                                 [note_id, pitch, volume])
        self._currently_playing.append(note_id)
        for param, value in properties.extra_playback_parameters.items():
            self.change_note_parameter(note_id, param, value.start_level() if hasattr(value, 'start_level') else value)

    def end_note(self, note_id: int) -> None:
        self.client.send_message("/{}/{}".format(self.message_prefix,
                                                 self.osc_message_addresses["end_note"]), [note_id])
        if note_id in self._currently_playing:
            self._currently_playing.remove(note_id)

    def change_note_pitch(self, note_id: int, new_pitch: float) -> None:
        self.client.send_message("/{}/{}".format(self.message_prefix, self.osc_message_addresses["change_pitch"]),
                                 [note_id, new_pitch])

    def change_note_volume(self, note_id: int, new_volume: float) -> None:
        self.client.send_message("/{}/{}".format(self.message_prefix, self.osc_message_addresses["change_volume"]),
                                 [note_id, new_volume])

    def change_note_parameter(self, note_id: int, parameter_name: str, new_value: float) -> None:
        self.client.send_message("/{}/{}/{}".format(
            self.message_prefix, self.osc_message_addresses["change_parameter"], parameter_name), [note_id, new_value])

    def set_max_pitch_bend(self, semitones: int) -> None:
        """
        This method does nothing in the case of an OSC-based implementation
        """
        pass

    def _to_dict(self):
        return {
            "port": self.port,
            "ip_address": self.ip_address,
            "message_prefix": self.message_prefix,
            "osc_message_addresses": self.osc_message_addresses
        }

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)
