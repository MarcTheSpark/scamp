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
import atexit
from clockblocks import Clock
import inspect
from ._dependencies import rtmidi
import threading
from .utilities import get_average_square_correlation
import functools
from collections import namedtuple
import time


def get_available_midi_input_devices():
    """
    Probes the available devices for midi input or output

    :return a list of tuples (port number, device name)
    """
    midi_in = rtmidi.MidiIn()
    return enumerate(midi_in.get_ports())


def print_available_midi_input_devices():
    """
    Prints a list of available ports and devices for midi input or output
    """
    print("MIDI Input Devices Available:")
    for port_number, device_name in get_available_midi_input_devices():
        print("   [Port {}]: {}".format(port_number, device_name))


def get_available_midi_output_devices():
    """
    Probes the available devices for midi input or output

    :return a list of tuples (port number, device name)
    """
    midi_out = rtmidi.MidiOut()
    return enumerate(midi_out.get_ports())


def print_available_midi_output_devices():
    """
    Prints a list of available ports and devices for midi input or output
    """
    print("MIDI Output Devices Available:")
    for port_number, device_name in get_available_midi_output_devices():
        print("   [Port {}]: {}".format(port_number, device_name))


def get_port_number_of_midi_device(device_name, input_or_output):
    """
    Get the port number of a given device based on its a fuzzy string match of its name.

    :param device_name: name of the device whose port to find
    :param input_or_output: either "input" or "output" (which kind of device to look for)
    :return: port number of the device, or None if not found
    """
    if input_or_output not in ("input", "output"):
        raise ValueError("input_or_output must be either \"input\" or \"output\"")

    device_list = get_available_midi_input_devices() if input_or_output == "input" \
        else get_available_midi_output_devices()

    best_match, best_correlation = None, 0
    for port, device in device_list:
        if device_name == device:
            return port
        else:
            correlation = get_average_square_correlation(device_name.lower(), device.lower())
            if correlation > best_correlation:
                best_match, best_correlation = port, correlation
    if best_correlation > 0.5:
        return best_match
    else:
        return None


def start_midi_listener(port_number_or_device_name, callback_function, clock):
    """
    Start a midi listener on a given port (or for the given device)

    :param port_number_or_device_name: either the port number to be used, or an device name for which the port
            number will be determined. (Fuzzy string matching is used to pick the device with closest name.)
    :type port_number_or_device_name: int or str
    :param callback_function: the callback function used when a new midi event arrives. Should take either one
        argument (the midi message) or two arguments (the midi message, and the dt since the last message)
    :param clock: the clock to rouse when this callback operates
    :type clock: Clock
    """

    port_number = get_port_number_of_midi_device(port_number_or_device_name, "input") \
        if isinstance(port_number_or_device_name, str) else port_number_or_device_name

    if port_number is None:
        raise ValueError("Could not find matching MIDI device.")
    elif port_number not in (x[0] for x in get_available_midi_input_devices()):
        raise ValueError("Invalid port number for midi listener.")

    callback_function_signature = inspect.signature(callback_function)
    if not 1 <= len(callback_function_signature.parameters) <= 2:
        raise AttributeError("MIDI callback function should take either one argument (the midi message) or "
                             "two arguments (the midi message and the time since the last message).")
    callback_accepts_dt = len(callback_function_signature.parameters) == 2

    from rtmidi.midiutil import open_midiinput
    midi_in, _ = open_midiinput(port_number)

    @functools.wraps(callback_function)
    def callback_wrapper(message, data=None):
        clock.rouse_and_hold()
        threading.current_thread().__clock__ = clock
        if callback_accepts_dt:
            callback_function(message[0], message[1])
        else:
            callback_function(message[0])
        threading.current_thread().__clock__ = None
        clock.release_from_suspension()

    midi_in.set_callback(callback_wrapper)
    return midi_in


_port_connections = {}


def get_port_connection(number, name):
    if (number, name) in _port_connections:
        return _port_connections[(number, name)]
    else:
        midi_out = rtmidi.MidiOut()
        if number is not None:
            midi_out.open_port(number, name)
        else:
            midi_out.open_virtual_port(name)
        _port_connections[(number, name)] = midi_out
        return midi_out


def _cleanup_port_connections():
    for midi_out_object in _port_connections.values():
        midi_out_object.delete()
    _port_connections.clear()


atexit.register(_cleanup_port_connections)


class SimpleRtMidiOut:
    """
    Wraps a single output of rtmidi to:
    a) make the calls a little easier and more specific, rather than all being send_message
    b) fail quietly. If rtmidi can't be loaded, then the user is alerted upon import, and
    from then on all rtmidi calls just don't do anything
    """

    def __init__(self, output_device=None, output_name=None):

        if rtmidi is not None:
            port_number = output_device if isinstance(output_device, int) \
                else get_port_number_of_midi_device(output_device, "output") if output_device is not None else None
            self.midiout = get_port_connection(port_number, output_name)

    def note_on(self, chan, pitch, velocity):
        if rtmidi is not None:
            self.midiout.send_message([0x90 + chan, pitch, velocity])

    def note_off(self, chan, pitch):
        if rtmidi is not None:
            self.midiout.send_message([0x80 + chan, pitch, 0])  # note on call of 0 velocity implementation
            self.midiout.send_message([0x90 + chan, pitch, 0])  # note off call implementation

    def pitch_bend(self, chan, value):
        assert 0 <= value < 16384
        if rtmidi is not None:
            # midi pitch bend data takes two midi data bytes; a least significant 7-bit number and
            # a most significant 7-bit number. These combine to form an integer from 0 to 16383
            lsb = value % 128
            msb = (value - lsb) // 128
            self.midiout.send_message([0xE0 + chan, lsb, msb])

    def expression(self, chan, value):
        if rtmidi is not None:
            self.midiout.send_message([0xB0 + chan, 11, value])

    def cc(self, chan, cc_number, value):
        if rtmidi is not None:
            self.midiout.send_message([0xB0 + chan, cc_number, value])


# -------------------------------------------- MIDI Channel Manager ----------------------------------------------


class NoFreeChannelError(Exception):

    def __init__(self, best_channel_to_free, notes_to_free):
        self.best_channel_to_free = best_channel_to_free
        self.notes_to_free = notes_to_free
        super().__init__()


# for each note in a MIDI channel, we want to keep track of its id, midi pitch, and start time
NoteInfo = namedtuple("NoteInfo", "note_id pitch start_time")


class MIDIChannelManager:

    """
    Keeps track of the states of a set of midi channels, and which notes are using them.

    :param num_channels: number of channels to manage
    :param ring_time: Duration after a note has finished during which we try not to treat the channel as free, since
        there may still be reverb, etc.
    :param time_func: function for determining the current time
    """

    def __init__(self, num_channels, ring_time=0.5, time_func=time.time):

        self.channels_info = [
            {
                "active_notes": [],  # contains (note_id, pitch, start_time)
                "last_note_end_time": float("-inf"),
                "pitch_bend": 0,
                "cc_values": {},
            }
            for _ in range(num_channels)
        ]
        self.time_func = time_func
        self.ring_time = ring_time

    @staticmethod
    def _cc_matches(channel_cc_values: dict, note_cc_values: dict):
        return channel_cc_values.keys() == note_cc_values.keys() and \
               all(note_cc_values[i] == channel_cc_values[i] for i in channel_cc_values.keys())

    def _get_best_channel_for_fixed_note(self, midi_pitch, pitch_bend, cc_values):
        # pick out the channels that:
        #   1) match all pitch_bend and cc_values
        #   2) does not currently have a note using this MIDI pitch slot
        matching_channels = [
            (i, channel_info) for i, channel_info in enumerate(self.channels_info)
            if pitch_bend == channel_info["pitch_bend"] and cc_values == channel_info["cc_values"]
            and not any(midi_pitch == note.pitch for note in channel_info["active_notes"])
        ]
        if len(matching_channels) > 0:
            # 3) preferentially, has a note already on it, since that reduces channel usage
            # (note that False values for the key get sorted before True values. So the first ones will be
            # the ones where len(index_and_channel_info[1]["active_notes"]) != 0)
            matching_channels.sort(
                key=lambda index_and_channel_info: len(index_and_channel_info[1]["active_notes"]) == 0
            )
            return matching_channels[0]
        else:
            return None

    def _get_free_channel(self):
        # in case we don't find any free channels that have been free for the full ring interval,
        # keep track of which ringing-only channel has the oldest finished note
        oldest_ringing_channel, oldest_finished_note_time = None, float("inf")
        for i, channel_info in enumerate(self.channels_info):
            if len(channel_info["active_notes"]) == 0:
                if self.time_func() > channel_info["last_note_end_time"] + self.ring_time:
                    # free channel with no notes recently finished during the ring interval. Go for it!
                    return i, channel_info
                else:
                    # free channel, but a recently finished note is still within the ring interval
                    if channel_info["last_note_end_time"] < oldest_finished_note_time:
                        oldest_ringing_channel = i, channel_info
                        oldest_finished_note_time = channel_info["last_note_end_time"]
        # see if there's a channel that was free, but still ringing
        if oldest_ringing_channel is not None:
            return oldest_ringing_channel
        # no free channel!
        return None

    def _get_best_channel_to_free(self):
        # there's no free channel, so we have to pick the least bad option
        channels_to_consider = [(i, channel_info) for i, channel_info in enumerate(self.channels_info)]
        # sort the options according to the channel that started a note least recently
        channels_to_consider.sort(
            key=lambda channel_num_and_info: max(note.start_time for note in channel_num_and_info[1]["active_notes"]))
        return channels_to_consider[0]

    def assign_note_to_channel(self, note_id, midi_pitch, pitch_bend, cc_values):
        """
        Assigns the given note to an appropriate channel, or raises a NoFreeChannelError if no free channel can be
        found. (The NoFreeChannelError contains a suggestion for what channel to free; this way the process using this
        channel manager can free the channel itself and try again to assign a note.)

        :param note_id: The id of the note so that we can remove it later
        :param midi_pitch: The (integer) midi pitch of the note
        :param pitch_bend: the pitch bend needed for this note, or "variable" if it is subject to change
        :param cc_values: a dictionary mapping cc_numbers to values (ranging from 0 to 1), or the string "variable" if
            any of the cc values change over the course of the note.
        """
        if pitch_bend == "variable" or cc_values == "variable":
            # this is a note that will change pitch or cc in a dynamic way; it needs its own channel
            channel = self._get_free_channel()
        else:
            # this is a fixed note, so we try to stick it on a channel that is already being used
            channel = self._get_best_channel_for_fixed_note(midi_pitch, pitch_bend, cc_values)
            if channel is None:
                # no good option that matches; just pick a free channel
                channel = self._get_free_channel()

        if channel is None:
            # there's not even a free channel, so throw an error
            channel_to_free, channel_info = self._get_best_channel_to_free()
            notes_to_free = list(self.channels_info[channel_to_free]["active_notes"])
            raise NoFreeChannelError(channel_to_free, notes_to_free)

        channel_num, channel_info = channel
        channel_info["active_notes"].append(NoteInfo(note_id, midi_pitch, self.time_func()))
        channel_info["pitch_bend"] = pitch_bend
        channel_info["cc_values"] = cc_values
        return channel_num

    def end_note(self, note_id):
        for channel_info in self.channels_info:
            for note in channel_info["active_notes"]:
                if note.note_id == note_id:
                    channel_info["active_notes"].remove(note)
                    channel_info["last_note_end_time"] = self.time_func()
                    return
        raise ValueError(f"Cannot find note id {note_id} to end it.")
