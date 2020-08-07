"""
SCAMP EXAMPLE: Live MIDI input and output

Demonstration of receiving and sending live midi input to and from a midi keyboard. Every note received by the keyboard
is immediately sent back to the keyboard a perfect fifth higher.
"""

#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  SCAMP (Suite for Computer-Assisted Music in Python)                                           #
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

s.print_available_midi_output_devices()

piano = s.new_midi_part("piano", midi_output_device=0, num_channels=15)

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
