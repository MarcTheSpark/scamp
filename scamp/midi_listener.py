from clockblocks import Clock
import inspect
import time
from .dependencies import rtmidi


def get_available_ports_and_devices():
    """
    returns a list of tuples (port number, device name)
    """
    midi_in = rtmidi.MidiIn()
    return enumerate(midi_in.get_ports())


def print_available_ports_and_devices():
    print("MIDI Devices Available:")
    for port_number, device_name in get_available_ports_and_devices():
        print("   [Port {}]: {}".format(port_number, device_name))


def get_port_number_of_device(device_name):
    for port, device in get_available_ports_and_devices():
        if device_name == device:
            return port
    return None


def start_midi_listener(port_number_or_device_name, callback_function, clock, time_resolution=0.005, synchronous=True):
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

    def _midi_listener(sub_clock):
        while True:
            message = midi_in.get_message()
            if message is not None:
                if callback_accepts_dt:
                    callback_function(message[0], message[1])
                else:
                    callback_function(message[0])
            if sub_clock is None:
                # asynchronous callback, so we use sleep
                time.sleep(time_resolution)
            else:
                sub_clock.wait(time_resolution)
    if synchronous:
        clock.fork(_midi_listener)
    else:
        clock.fork_unsynchronized(_midi_listener, args=(None, ))
