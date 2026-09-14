"""
SCAMP Example: Play Chord

Demonstrates `ScampInstrument.play_chord` by playing a famous progression, and then playing it a few more times
randomly up and down the keyboard.
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
import random

# fixed random seed for reproducibility
random.seed(42)

s = Session()
s.tempo = 72

piano = s.new_part("piano")

# a famous chord progression
piano.play_chord([53, 59, 63, 68], 0.8, 2)
piano.play_chord([52, 56, 62, 71], 0.6, 1)


# and then the same progression bouncing up and down the piano
# oh, and let's accelerate, why not
set_tempo_target(144, Moment.after_beats(6))
for _ in range(8):
    t = random.randint(-24, 24)
    piano.play_chord([53 + t, 59 + t, 63 + t, 68 + t], 0.8, 0.5)
    piano.play_chord([52 + t, 56 + t, 62 + t, 71 + t], 0.6, 0.5, "staccato")
