"""
Demonstration of receiving and sending live midi input to and from a midi keyboard. 
"""

from scamp import *

s = Session()

s.print_available_midi_ports_and_devices()

piano = s.new_midi_part("piano", midi_output_device=1, num_channels=15)

# dictionary mapping keys that are down to the NoteHandles used to manipulate them.
notes_started = {}


def midi_callback(midi_message):
    code, pitch, volume = midi_message
    if volume > 0 and 144 <= code <= 159:
        notes_started[pitch] = piano.start_note(pitch + 7, volume/127)
    elif (volume == 0 and 144 <= code <= 159 or 128 <= code <= 143) and pitch in notes_started:
        notes_started[pitch].end()


s.register_midi_listener(0, midi_callback)
s.wait_forever()
