"""
SCAMP Example: Live MIDI input and output

Demonstration of receiving and sending live midi input to and from a midi keyboard.
Every note received by the keyboard is echoed back to the midi device half a second later
at 75% volume.
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

s.print_available_midi_output_devices()

# This assumes we want the first listed MIDI device.
# To use a different device, give the number or name that
# you get from printing available devices above.
piano = s.new_midi_part("piano", midi_output_device=0,
                        num_channels=15)


# dictionary mapping keys that are down to the NoteHandles used to manipulate them.
notes_started = {}


def start_note(pitch, volume):
    # start the copy-cat note and store the handle to it to end it later
    notes_started[pitch] = piano.start_note(pitch, volume)


def end_note(pitch):
    # end the copy-cat note (if one has started)
    if pitch in notes_started:
        notes_started[pitch].end()
        del notes_started[pitch]


def midi_callback(midi_message):
    code, pitch, volume = midi_message
    # note on event in any channel
    if volume > 0 and 144 <= code <= 159:
        # fork a copy-cat note to start a 5th higher at 75% volume after 0.5 seconds
        normalized_volume = (volume / 127)
        s.fork(start_note, args=(pitch + 7, normalized_volume * 0.75), when=Moment.after_time(0.5))
    # note off (or note on with velocity 0) event in any channel
    elif (volume == 0 and 144 <= code <= 159 or 128 <= code <= 143):
        # fork the copy-cat note a 5th higher to end after 0.5 seconds
        s.fork(end_note, args=(pitch + 7, ), when=Moment.after_time(0.5))


s.register_midi_listener(0, midi_callback)
s.wait_forever()
