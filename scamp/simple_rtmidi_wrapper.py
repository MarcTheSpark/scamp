from ._dependencies import rtmidi


def get_best_name_match(names_list, desired_name):
    """
    Looks initially for first exact case-sensitive match for desired_name in names_list. Then looks for
    first case insensitive match. Then looks for anything containing desired_name (case insensitive).
    Outputs None if this all fails

    :param names_list: list of names to search through
    :param desired_name: name to match
    :return: str of best match to desired name in names_list
    """
    if desired_name is None:
        return None
    if desired_name in names_list:
        return names_list.index(desired_name)
    lower_case_list = [s.lower() for s in names_list]
    lower_case_desired_name = desired_name.lower()
    if lower_case_desired_name in lower_case_list:
        return lower_case_list.index(lower_case_desired_name)
    for lower_case_name in lower_case_list:
        if lower_case_desired_name in lower_case_name:
            return lower_case_list.index(lower_case_name)
    return None


def get_available_midi_output_devices():
    if rtmidi is None:
        print("python-rtmidi was not found; cannot check for available ports.")
        return None
    else:
        midiout = rtmidi.MidiOut()
        ports = midiout.get_ports()
        del midiout
        return ports


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
                available_ports = self.midiout.get_ports()
                chosen_output = get_best_name_match(available_ports, output_device)
                if chosen_output is not None:
                    self.midiout.open_port(chosen_output, name=output_name)
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
