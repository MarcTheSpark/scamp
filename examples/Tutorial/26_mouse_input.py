"""
SCAMP EXAMPLE: Mouse Input

(WARNING: consumes mouse events and makes the mouse otherwise unresponsive. To avoid this, you can remove the
suppress=True flag under register_mouse_listener)

Demonstration of receiving computer mouse events and using them to play notes based on x and y position.
Notes are started on mouse down and released on mouse up.  Left click plays a piano note, and right click plays
a flute note. X position controls pitch, Y controls volume. By moving the mouse after clicking, the pitch can be bent
up and down and the volume can be changed.
"""

from scamp import *

s = Session()

piano = s.new_part("piano")
flute = s.new_part("flute")

# information about a note that has been started
note_started = None


def mouse_down(x, y, button):
    global note_started
    pitch = 50 + 49 * x
    note_started = {
        "handle": (piano if button == "left" else flute).start_note(pitch, 1 - 0.8 * y),
        "start_pitch": pitch,
        "start_x": x
    }


def mouse_up(x, y, button):
    global note_started
    if note_started is not None:
        note_started["handle"].end()
        note_started = None


def mouse_move(x, y):
    if note_started is not None:
        note_started["handle"].change_pitch(note_started["start_pitch"] + 4 * (x - note_started["start_x"]), 0.1)
        note_started["handle"].change_volume(1 - 0.8*y, 0.1)


# note: suppress=True causes mouse events to be consumed by this script, effectively disabling the mouse
s.register_mouse_listener(on_move=mouse_move, on_press=mouse_down, on_release=mouse_up,
                          relative_coordinates=True, suppress=True)
s.wait_forever()
