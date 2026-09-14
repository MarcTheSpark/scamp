"""
SCAMP Example: Tempo Change

Same as Hello World example, but repeatedly, with changing tempi.
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

# Start with an initial tempo of 100
s.tempo = 100

# add a new violin part to the session
violin = s.new_part("Violin")


for pitch in [60, 64, 67, 72]:
    violin.play_note(pitch, 1, 0.5)

# you can change tempo at any time; not just at the beginning
s.tempo = 40
for pitch in [60, 64, 67, 72]:
    violin.play_note(pitch, 1, 0.5)

# you can also do an accelerando/decelerando, specifying
# a moment at which to reach the goal tempo
set_tempo_target(150, Moment.after_beats(6))
for pitch in [60, 64, 67, 72] * 4:
    violin.play_note(pitch, 1, 0.5)