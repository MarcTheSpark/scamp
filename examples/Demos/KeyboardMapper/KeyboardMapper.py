"""
A script written at the request of Paul Timmermans, in which different pitches or ranges of pitches
on the keyboard can be mapped to particular instruments and chords. The heart of the script is the
dictionary `pitch_to_instrument_and_pitches`, which expresses, for each key, which pitches and on
which instrument should be played.
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

# This is where you define all of the instrument that you want to play back notes with.
# The `note_on_and_off_only=True` flag is helpful in keeping the midi messages simple if
# your not doing any pitch bending, glissandi, microtonal stuff, or dynamic envelopes.
# The `new_midi_part` call will open an outgoing midi stream, in this case to IAC, which
# is a virtual midi cable that can be used (on macs) to route playback between applications
piano = s.new_midi_part("pianoteq", "IAC", note_on_and_off_only=True)
# The `new_part` calls create parts that play back using the default soundfont
flute = s.new_part("flute", note_on_and_off_only=True)
clarinet = s.new_part("clarinet", note_on_and_off_only=True)

# This is where the magic happens! Each entry in this dictionary determines what happens
# when you play a pitch in a certain key or range of keys.
pitch_to_instrument_and_pitches = {
    # this line says that if you play midi pitch 55, it will come out as pitch 77, played by the clarinet
    55: [clarinet, 77],
    # this line says that if you play midi pitch 43, it will come out as the cluster [60, 61, 62, 63] played by clarinet
    43: [clarinet, [60, 61, 62, 63]],
    # this line says that if you play a pitch between 65-72, it will come out as a chord played by the flute
    # consisting of the note two half steps higher and two half-steps lower. "p" stands for the particular
    # pitch that you play, since this is operating on a range of pitches
    # Note the quotes! The strings used here aren't really a standard python thing; it was just the easiest way
    # of making it work.
    "65-72": [flute, "[p-2, p+2]"],
    # this line says what to do if you play a pitch that isn't covered by the lines above. In this case, we play
    # back with a piano, up an octave (since "p" is the pitch you played, "p+12" is that pitch up an octave.
    "default": [piano, "p+12"]
}

# Put here the name of the device MIDI messages are coming in from
MIDI_INPUT_DEVICE = "E-MU"

# # Uncomment these lines if you want to see which midi input and output devices are available
# print_available_midi_input_devices()
# print_available_midi_output_devices()

# --------------------------------------------- IMPLEMENTATION -----------------------------------------------

# ----- process pitch_to_instrument_and_pitches -----
processed_pitch_to_instrument_and_pitches = {}
for key, value in pitch_to_instrument_and_pitches.items():
    if isinstance(key, str) and "-" in key:
        start_pitch, end_pitch = key.split("-")
        for p in range(int(start_pitch), int(end_pitch) + 1):
            processed_pitch_to_instrument_and_pitches[p] = value
for key, value in pitch_to_instrument_and_pitches.items():
    if not isinstance(key, str):
        processed_pitch_to_instrument_and_pitches[key] = value
            
for key, value in processed_pitch_to_instrument_and_pitches.items():
    instrument, pitches = value
    if isinstance(pitches, str) and key != "default":
        processed_pitch_to_instrument_and_pitches[key] = [instrument, eval(pitches, {}, {"p": key})]

processed_pitch_to_instrument_and_pitches["default"] = pitch_to_instrument_and_pitches["default"]
notes_down = [[] for _ in range(128)]
pedal_held_notes = [[] for _ in range(128)]
pedal_down = False


def midi_callback(midi_message):
    global notes_down, pedal_held_notes, pedal_down
    # function that handles any incoming midi messages from the keyboard
    print(midi_message)
    code, pitch, volume = midi_message
    if volume > 0 and code == 144:
        # note on message causes us to fork a new moonlight sonata gesture at the given pitch and volume
        if pitch in processed_pitch_to_instrument_and_pitches:
            instrument, pitches = processed_pitch_to_instrument_and_pitches[pitch]
        else:
            instrument, pitches = processed_pitch_to_instrument_and_pitches["default"]
            if isinstance(pitches, str):
                pitches = eval(pitches, {}, {"p": pitch})
        if hasattr(pitches, '__len__'):
            notes_down[pitch].append(instrument.start_chord(pitches, volume / 127))
        else:
            notes_down[pitch].append(instrument.start_note(pitches, volume / 127))
    elif volume == 0 and code == 144 or code == 143 or code == 128:
        # note off message (or note on message with 0 velocity, which is sometimes how it's implemented)
        # we use it to kill the gesture running for the note at the given pitch
        if pedal_down:
            pedal_held_notes[pitch].extend(notes_down[pitch])
            notes_down[pitch].clear()
        else:
            for note in notes_down[pitch]:
                note.end()
            notes_down[pitch].clear()
    elif code == 176 and pitch == 64:
        # pedal change messages just get passed straight along to the MIDI_OUTPUT_DEVICE
        # (with some warping of the values)
        pedal_down = volume > 0
        if volume == 0:
            for pitch_notes in pedal_held_notes:
                for note in pitch_notes:
                    note.end()
                pitch_notes.clear()


s.register_midi_listener("E-MU", midi_callback)
s.wait_forever()
