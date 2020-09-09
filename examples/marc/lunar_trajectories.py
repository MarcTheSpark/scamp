"""
Interactive piano script for the first movement of "Lunar Trajectories".
The `notes` list below is a list of all the notes played by the middle arpeggio part in the first movement
of the Moonlight Sonata, in order. If a pitch is in that list, then when it is depressed, the piano reacts
by playing whichever pitches follow that pitch the first time it occurs in the list. If a pitch is not in
the list, then instead we look for the same pitch class but in a different octave, and follow it up by the
notes that follow that pitch (transposed back up or down by however many octaves).

Every pitch class appears in the first movement, so we don't have the issue of searching for a pitch class
that doesn't occur.
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


# the input and output device can be the same or different
# for instance, you might want to take midi in from the keyboard,
# but send any note playback messages to a softsynth like pianoteq
MIDI_INPUT_DEVICE = "E-MU"
MIDI_OUTPUT_DEVICE = "E-MU"

# --------------------------------------- Setup -------------------------------------------
# Here we pre-process the list of notes, so that we know, for every pitch that the performer
# might play, where in that list of notes it first occurs, and what(if any) transposition
# we need to apply. We also set up the rate at which notes playback throughout the keyboard


# create a mapping from midi pitch to the rate of note playback (rate is in notes/second)
gesture_rate_by_pitch = {
    p: 3 * 2 ** ((p - 60) / 12)
    for p in range(21, 109)
}


# a list of all the pitches from the middle arpeggio part
# in the first movement of the Moonlight Sonata
notes = [56, 61, 64, 56, 61, 64, 56, 61, 64, 56, 61, 64, 56, 61, 64, 56, 61, 64, 56, 61, 64,
         56, 61, 64, 57, 61, 64, 57, 61, 64, 57, 62, 66, 57, 62, 66, 56, 60, 66, 56, 61, 64,
         56, 61, 63, 54, 60, 63, 52, 56, 61, 56, 61, 64, 56, 61, 64, 56, 61, 64, 56, 63, 66,
         56, 63, 66, 56, 63, 66, 56, 63, 66, 56, 61, 64, 56, 61, 64, 57, 61, 66, 57, 61, 66,
         56, 59, 64, 56, 59, 64, 57, 59, 63, 57, 59, 63, 56, 59, 64, 56, 59, 64, 56, 59, 64,
         56, 59, 64, 55, 59, 64, 55, 59, 64, 55, 59, 64, 55, 59, 64, 55, 59, 65, 55, 59, 65,
         55, 59, 65, 55, 59, 65, 55, 60, 64, 55, 59, 64, 55, 61, 64, 54, 61, 64, 54, 59, 62,
         54, 59, 62, 55, 59, 61, 52, 59, 61, 54, 59, 62, 54, 59, 62, 54, 58, 61, 54, 58, 61,
         59, 62, 66, 59, 62, 66, 59, 63, 66, 59, 63, 66, 59, 64, 67, 59, 64, 67, 59, 64, 67,
         59, 64, 67, 59, 63, 66, 59, 63, 66, 59, 63, 66, 59, 63, 66, 59, 64, 67, 59, 64, 67,
         59, 64, 67, 59, 64, 67, 59, 63, 66, 59, 63, 66, 59, 62, 65, 59, 62, 65, 59, 61, 68,
         59, 61, 68, 57, 61, 66, 57, 61, 66, 55, 59, 62, 55, 59, 62, 54, 57, 63, 54, 57, 63,
         49, 54, 57, 49, 54, 57, 49, 54, 56, 49, 53, 56, 54, 57, 61, 57, 61, 66, 61, 66, 69,
         61, 66, 69, 61, 68, 71, 61, 68, 71, 61, 68, 71, 61, 68, 71, 61, 66, 69, 61, 66, 69,
         60, 66, 69, 61, 66, 69, 63, 66, 68, 63, 66, 68, 63, 66, 68, 63, 66, 68, 64, 68, 73,
         64, 68, 73, 63, 66, 69, 61, 64, 70, 72, 60, 63, 68, 60, 63, 69, 60, 63, 66, 60, 63,
         60, 63, 56, 60, 63, 57, 60, 63, 54, 60, 63, 52, 64, 68, 73, 64, 68, 76, 64, 68, 73,
         64, 68, 52, 56, 61, 52, 56, 64, 52, 56, 61, 52, 56, 51, 57, 54, 60, 57, 63, 60, 66,
         63, 69, 66, 72, 52, 61, 56, 64, 61, 68, 64, 73, 68, 76, 73, 68, 61, 67, 64, 70, 67,
         73, 70, 76, 73, 79, 76, 82, 66, 72, 69, 75, 72, 78, 75, 81, 78, 84, 81, 87, 84, 78,
         81, 75, 78, 72, 75, 69, 72, 66, 69, 63, 66, 60, 63, 57, 60, 54, 57, 51, 54, 49, 54,
         57, 48, 54, 56, 57, 56, 54, 51, 54, 57, 49, 54, 57, 48, 54, 56, 57, 56, 54, 50, 54,
         57, 49, 54, 57, 48, 54, 56, 57, 56, 54, 49, 52, 61, 49, 52, 61, 51, 57, 61, 51, 57,
         61, 51, 56, 60, 51, 54, 60, 52, 56, 61, 56, 61, 64, 56, 61, 64, 56, 61, 64, 56, 63,
         66, 56, 63, 66, 56, 63, 66, 56, 63, 66, 56, 61, 64, 56, 61, 64, 57, 61, 66, 57, 61,
         66, 56, 59, 64, 56, 59, 64, 57, 59, 63, 57, 59, 63, 56, 59, 64, 59, 64, 68, 59, 64,
         68, 59, 64, 68, 59, 66, 69, 59, 66, 69, 59, 66, 69, 59, 66, 69, 59, 64, 68, 59, 64,
         68, 60, 66, 68, 61, 64, 68, 63, 66, 68, 63, 66, 68, 64, 68, 73, 64, 68, 73, 62, 66,
         69, 62, 66, 69, 60, 66, 68, 60, 66, 68, 61, 64, 68, 61, 64, 68, 61, 65, 68, 61, 65,
         68, 61, 66, 69, 61, 66, 69, 61, 66, 69, 61, 66, 69, 61, 65, 68, 61, 65, 68, 61, 65,
         68, 61, 65, 68, 61, 66, 69, 61, 66, 69, 61, 66, 69, 61, 66, 69, 61, 65, 68, 61, 65,
         68, 61, 66, 69, 61, 66, 69, 59, 66, 69, 59, 66, 69, 59, 66, 69, 59, 64, 68, 57, 64,
         68, 57, 63, 66, 56, 63, 66, 56, 61, 64, 54, 61, 63, 54, 61, 63, 56, 61, 63, 57, 61,
         63, 56, 61, 64, 56, 61, 64, 54, 60, 63, 54, 60, 63, 52, 56, 61, 56, 61, 64, 56, 61,
         64, 56, 61, 64, 56, 63, 66, 56, 63, 66, 56, 63, 66, 56, 63, 66, 56, 64, 61, 68, 64,
         73, 68, 76, 73, 80, 76, 73, 72, 75, 69, 72, 66, 69, 63, 66, 57, 60, 56, 54, 52, 61,
         64, 61, 68, 64, 73, 68, 76, 73, 80, 76, 73, 72, 75, 69, 72, 66, 69, 63, 66, 57, 60,
         56, 54, 52, 56, 61, 64, 61, 56, 49, 52, 56, 61, 56, 52, 44, 49, 52, 56, 52, 49, 44,
         49, 44, 40, 44, 40, 37]


# dictionary which will map each pitch played to the index within the arpeggio notes
pitch_to_note_index = {}
# dictionary which will map each pitch played to the extra transposition needed
pitch_to_gesture_transposition = {}


# this code populates the pitch_to_note_index and pitch_to_gesture_transposition dictionaries
# so that we know, for each pitch that might be played, where to find that in the notes list
# and what if any transposition to apply.
represented_notes = set(notes)
for pitch in range(21, 108):
    transpose = 0

    if pitch not in represented_notes:
        closest_of_same_pc = None
        min_distance = float("inf")

        for p in represented_notes:
            if p % 12 == pitch % 12 and abs(p - pitch) < min_distance:
                closest_of_same_pc = p
                min_distance = abs(p - pitch)

        transpose = pitch - closest_of_same_pc
        search_pitch = closest_of_same_pc
    else:
        search_pitch = pitch

    search_start = 0
    try:
        while notes.index(search_pitch, search_start) in pitch_to_note_index.values():
            search_start = notes.index(search_pitch, search_start) + 1
    except ValueError:
        search_start -= 1

    pitch_to_note_index[pitch] = notes.index(search_pitch, search_start)
    pitch_to_gesture_transposition[pitch] = transpose
    

# -------------------------------------- The main script ------------------------------------------

s = Session()

# uncomment these lines to print out the available MIDI output and input devices
# s.print_available_midi_input_devices()
# s.print_available_midi_output_devices()

# this instrument will playback the generated MIDI notes
piano = s.new_midi_part("piano", MIDI_OUTPUT_DEVICE, num_channels=1)


# used to keep track of which pitches are being held and therefore currently have gestures running
gestures_running = {}


def play_gesture(pitch, volume):
    # this is the gesture that is forked every time a note with the given pitch and volume is depressed
    gestures_running[pitch] = True
    # all notes play back for one "beat", but we turn up or down the speed of this gesture's clock
    # depending on which pitch was played
    current_clock().rate = gesture_rate_by_pitch[pitch]
    
    next_pitches = notes[pitch_to_note_index[pitch]:]
    wait(1)
    for p in next_pitches:
        if not gestures_running[pitch]:
            # if gestures_running[pitch] is now false, it means we lifted the key, so break out of the gesture
            break
        # play the next note of the gesture
        piano.play_note(p + pitch_to_gesture_transposition[pitch], volume, 1)
        # each note fades out relative to the previous one
        volume *= 0.9


def midi_callback(midi_message):
    # function that handles any incoming midi messages from the keyboard
    code, pitch, volume = midi_message
    if volume > 0 and code == 144:
        # note on message causes us to fork a new moonlight sonata gesture at the given pitch and volume
        fork(play_gesture, args=(pitch, volume / 127))
    elif volume == 0 and code == 144 or code == 143 or code == 128:
        # note off message (or note on message with 0 velocity, which is sometimes how it's implemented)
        # we use it to kill the gesture running for the note at the given pitch
        gestures_running[pitch] = False
    elif code == 176 and pitch == 64:
        # pedal change messages just get passed straight along to the MIDI_OUTPUT_DEVICE
        # (with some warping of the values)
        piano.send_midi_cc(64, (volume/127) ** 0.3)


# have the session forward any incoming midi messages 
s.register_midi_listener(MIDI_INPUT_DEVICE, midi_callback)
# since everything is driven by MIDI input, we ask the session to wait forever
# so that the program doesn't just end immediate.y
s.wait_forever()
