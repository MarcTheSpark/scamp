"""
Demonstration of receiving computer keyboard events and using them to play notes based on the key number.
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


s.register_keyboard_listener(on_press=key_down, on_release=key_up, suppress=True)
s.wait_forever()
