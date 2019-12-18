from clockblocks import Clock
import inspect
import time
from ._dependencies import rtmidi
import threading


def get_available_ports_and_devices():
    """
    :return a list of tuples (port number, device name)
    """
    midi_in = rtmidi.MidiIn()
    return enumerate(midi_in.get_ports())


def print_available_ports_and_devices():
    """
    Prints a list of available ports and devices
    """
    print("MIDI Devices Available:")
    for port_number, device_name in get_available_ports_and_devices():
        print("   [Port {}]: {}".format(port_number, device_name))


def get_port_number_of_device(device_name):
    """
    Get the port number of a given device based on its name.
    TODO: allow fuzzy string matching

    :param device_name: name of the device whose port to find
    :return: port number of the device, or None if not found
    """
    for port, device in get_available_ports_and_devices():
        if device_name == device:
            return port
    return None


def start_midi_listener(port_number_or_device_name, callback_function, clock, time_resolution=0.005):
    """
    Start a midi listener for a given device / port

    :param port_number_or_device_name: either the port number to be used, or an device name for which the port
            number will be determined.
    :param callback_function: the callback function used when a new midi event arrives. Should take either one
        argument (the midi message) or two arguments (the midi message, and the dt since the last message)
    :param clock: the master clock to rouse when this callback operates
    :param time_resolution: time resolution used in checking for midi events
    """
    port_number = get_port_number_of_device(port_number_or_device_name) \
        if isinstance(port_number_or_device_name, str) else port_number_or_device_name

    assert isinstance(clock, Clock)

    callback_function_signature = inspect.signature(callback_function)
    assert 1 <= len(callback_function_signature.parameters) <= 2, \
        "MIDI callback function should take either one argument (the midi message) or two arguments (the midi " \
        "message and the time since the last message)."
    callback_accepts_dt = len(callback_function_signature.parameters) == 2

    midi_in = rtmidi.MidiIn()
    assert port_number is not None and 0 <= port_number < midi_in.get_port_count(), "Invalid midi listener port number."
    midi_in.open_port(port_number)

    def _midi_listener():
        while True:
            message = midi_in.get_message()
            if message is not None:
                clock.rouse_and_hold()
                threading.current_thread().__clock__ = clock
                if callback_accepts_dt:
                    callback_function(message[0], message[1])
                else:
                    callback_function(message[0])
                threading.current_thread().__clock__ = None
                clock.release_from_suspension()
            else:
                time.sleep(time_resolution)

    clock.fork_unsynchronized(_midi_listener)
