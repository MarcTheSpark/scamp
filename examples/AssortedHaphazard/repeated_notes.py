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

# flute = s.new_part("flute", num_channels=3)

# while True:
#     flute.play_note([60, 70, 60], [0.7, 0.4, 0.7], 3, blocking=False)
#     wait(1)
#     flute.play_note([70, 80, 70], [0.7, 0.4, 0.7], 3, blocking=False)
#     wait(1)
#     flute.play_note([80, 90, 80], [0.7, 0.4, 0.7], 3, blocking=False)
#     wait(1)

piano = s.new_part("piano", num_channels=4)

while True:
    piano.play_note(60, 0.8, 0.15, blocking=False)
    piano.play_note(62.5, 0.8, 0.15, blocking=False)
    piano.play_note(63.5, 0.8, 0.15, blocking=False)
    piano.play_note(67.5, 0.8, 0.15, blocking=False)
    wait(0.1)


