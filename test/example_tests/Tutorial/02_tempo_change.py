"""
SCAMP Example: Tempo Change

Same as Hello World example, but at half-tempo.
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

# import the scamp namespace
from scamp import *
# construct a session object
s = Session()
s.fast_forward_in_beats(float("inf"))

# change to half of default tempo
s.tempo = 30

# add a new violin part to the session
violin = s.new_part("Violin")
# looping through the MIDI pitches
# of a C major arpeggio...
for pitch in [60, 64, 67, 72]:
    # play each pitch sequentially
    # with volume of 1 (full volume)
    # and duration of half a beat
    violin.play_note(pitch, 1, 0.5)


def test_results():
    return [True]
