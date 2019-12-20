from clockblocks import Clock
import inspect
from ._dependencies import rtmidi
import threading
from .utilities import get_average_square_correlation
from rtmidi.midiutil import open_midiinput


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
    Get the port number of a given device based on its a fuzzy string match of its name.

    :param device_name: name of the device whose port to find
    :return: port number of the device, or None if not found
    """
    best_match, best_correlation = None, 0
    for port, device in get_available_ports_and_devices():
        if device_name == device:
            return port
        else:
            correlation = get_average_square_correlation(device_name, device)
            if correlation > best_correlation:
                best_match, best_correlation = port, correlation
    return best_match


def start_midi_listener(port_number_or_device_name, callback_function, clock):
    """
    Start a midi listener for a given device / port

    :param port_number_or_device_name: either the port number to be used, or an device name for which the port
            number will be determined.
    :param callback_function: the callback function used when a new midi event arrives. Should take either one
        argument (the midi message) or two arguments (the midi message, and the dt since the last message)
    :param clock: the clock to rouse when this callback operates
    """
    port_number = get_port_number_of_device(port_number_or_device_name) \
        if isinstance(port_number_or_device_name, str) else port_number_or_device_name

    assert isinstance(clock, Clock)

    callback_function_signature = inspect.signature(callback_function)
    assert 1 <= len(callback_function_signature.parameters) <= 2, \
        "MIDI callback function should take either one argument (the midi message) or two arguments (the midi " \
        "message and the time since the last message)."
    callback_accepts_dt = len(callback_function_signature.parameters) == 2

    if port_number is None:
        raise ValueError("Could not find matching MIDI device.")
    elif port_number not in (x[0] for x in get_available_ports_and_devices()):
        raise ValueError("Invalid port number for midi listener.")

    midi_in, _ = open_midiinput(port_number)

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
