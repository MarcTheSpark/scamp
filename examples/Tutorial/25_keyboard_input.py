"""
SCAMP EXAMPLE: Computer Keyboard Input

(WARNING: consumes key events and makes the keyboard otherwise unresponsive. To avoid this, you can remove the
suppress=True flag under register_keyboard_listener)

Demonstration of receiving computer keyboard events and using them to play notes based on the key number. Any key
whose number code lies within a reasonable range triggers the playback of a note of that MIDI pitch.
"""

from scamp import *

s = Session()

piano = s.new_part("piano")

# dictionary mapping keys that are down to the NoteHandles used to manipulate them.
notes_started = {}


def key_down(name, number):
    if 20 < number < 110 and number not in notes_started:
        notes_started[number] = piano.start_note(number, 0.5)


def key_up(name, number):
    if 20 < number < 110 and number in notes_started:
        notes_started[number].end()
        del notes_started[number]


# note: suppress=True causes keyboard events to be consumed by this script, effectively disabling the keyboard
s.register_keyboard_listener(on_press=key_down, on_release=key_up, suppress=True)
s.wait_forever()
