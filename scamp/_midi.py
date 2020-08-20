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

from clockblocks import Clock
import inspect

from ._dependencies import rtmidi
import threading
from .utilities import get_average_square_correlation
import functools


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


def get_port_number_of_midi_device(device_name, input_or_output="input"):
    """
    Get the port number of a given device based on its a fuzzy string match of its name.

    :param device_name: name of the device whose port to find
    :param input_or_output: either "input" or "output" (which kind of device to look for)
    :return: port number of the device, or None if not found
    """
    if input_or_output not in ("input", "output"):
        raise ValueError("input_or_output must be either \"input\" or \"output\"")

    best_match, best_correlation = None, 0
    for port, device in get_available_midi_input_devices():
        if device_name == device:
            return port
        else:
            correlation = get_average_square_correlation(device_name.lower(), device.lower())
            if correlation > best_correlation:
                best_match, best_correlation = port, correlation
    return best_match


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


class SimpleRtMidiOut:
    """
    Wraps a single output of rtmidi to:
    a) make the calls a little easier and more specific, rather than all being send_message
    b) fail quietly. If rtmidi can't be loaded, then the user is alerted upon import, and
    from then on all rtmidi calls just don't do anything
    """
    def __init__(self, output_device=None, output_name=None):

        if rtmidi is not None:
            self.midiout = rtmidi.MidiOut()
            # # FOR SOME REASON, in the python-rtmidi examples, they call `del midiout` at the end
            # # I don't think it's necessary, and it causes an annoying error on exit, so it's commented out
            # def cleanup():
            #     del self.midiout
            # atexit.register(cleanup)
            if isinstance(output_device, int):
                self.midiout.open_port(output_device, name=output_name)
            else:
                output_port = get_port_number_of_midi_device(output_device) if output_device is not None else None
                if output_port is not None:
                    self.midiout.open_port(output_port, name=output_name)
                else:
                    self.midiout.open_virtual_port(name=output_name)

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