"""
SCAMP Example: Note Spelling

Ways to control pitch spelling: session/instrument defaults, keys, and per-note settings.

Tags: pitch spelling, note properties
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

s.tempo = 120
s.start_transcribing()

pitches = range(60, 85)
note_lengths = [0.25] * 24 + [2.0]

# Use session and instrument defaults to specify what happens when no explicit spelling is given to play_note:
#     s.default_spelling_policy = "A major"
#     piano.default_spelling_policy = "Ab major"
# Instrument defaults override session defaults

# Here are several options for spelling a chromatic scale:

s.fast_forward()

# 1) Don't specify any spelling information for the individual note played
# Reverts to defaults with the following order of priority:
#   - instrument default spelling policy
#   - session default spelling policy
#   - scamp default spelling policy (as defined in engravingSettings.json)
for pitch, length in zip(pitches, note_lengths):
    piano.play_note(pitch, 1.0, length)

# 2) Spell the note with a sharp / flat no matter what. Even white keys will be spelled with double-sharps.
# (Since the spelling is explicit at the note level, instrument and session defaults are ignored.)
for pitch, length in zip(pitches, note_lengths):
    piano.play_note(pitch, 1.0, length, "#")
for pitch, length in zip(pitches, note_lengths):
    piano.play_note(pitch, 1.0, length, "b")

# 3) Spell the note with a sharp / flat if it's a black key, otherwise no accidental
for pitch, length in zip(pitches, note_lengths):
    piano.play_note(pitch, 1.0, length, "sharps")
for pitch, length in zip(pitches, note_lengths):
    piano.play_note(pitch, 1.0, length, "flats")

# 4) Spell the note based on a given key center
for pitch, length in zip(pitches, note_lengths):
    piano.play_note(pitch, 1.0, length, "key: F")
for pitch, length in zip(pitches, note_lengths):
    piano.play_note(pitch, 1.0, length, "key: D locrian")

performance = s.stop_transcribing()

performance.to_score().show()
