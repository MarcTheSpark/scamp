"""
SCAMP EXAMPLE: Computer Keyboard Input

(WARNING: consumes key events and makes the keyboard otherwise unresponsive. To avoid this, you can remove the
suppress=True flag under register_keyboard_listener)

Demonstration of receiving computer keyboard events and using them to play notes based on the key number. Any key
whose number code lies within a reasonable range triggers the playback of a note of that MIDI pitch.
"""

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
