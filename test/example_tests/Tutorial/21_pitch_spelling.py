"""
SCAMP Example: Pitch Spelling

Demonstrates the ability to define note pitch spelling using the optional properties argument to "play_note". This can
be done by explicitly setting it, or by defining the key in which it resides.
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
s.fast_forward_in_beats(float("inf"))

piano = s.new_part("piano")

s.start_transcribing()

# play and spell a note with a flat no matter what
piano.play_note(63, 1.0, 1.0, "b")

# play and spell a note with a sharp no matter what
piano.play_note(63, 1.0, 1.0, "#")

# define some notes and durations
pitches = [65, 63, 61, 60]
durations = [1/3] * 3 + [1]

# play them and spell them in F minor
for pitch, dur in zip(pitches, durations):
    piano.play_note(pitch, 1.0, dur, "key: F minor")

# play them and spell them in B major
for pitch, dur in zip(pitches, durations):
    piano.play_note(pitch, 1.0, dur, "key: B major")


performance = s.stop_transcribing()

s.kill()


def test_results():
    return (
        performance,
        performance.to_score()
    )

