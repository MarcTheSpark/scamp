"""
SCAMP Example: TimeVaryingParameter Extension

A script using the context-sensitive :class:`~expenvelope.envelope.Envelope` wrapper :class:`TimeVaryingParameter`,
which reads into the underlying envelope at the current clock   's beat or time when called.
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
from scamp_extensions.utilities import TimeVaryingParameter


s = Session()

piano = s.new_part("piano")


def play_gesture(center_pitch, width, length):
    pitch_shape = TimeVaryingParameter.from_levels([0, width, -width, -width/2, -width, 0], length=length)
    volume_shape = TimeVaryingParameter([1, 0.4, 1], [length * 0.1, length * 0.9])
    while current_clock().beat < length:
        piano.play_note(int(center_pitch + pitch_shape()), volume_shape(), 0.25)


width_param = TimeVaryingParameter([4, 20, 0], [30, 30])
center_pitch_param = TimeVaryingParameter([60, 80, 40, 60], [20, 20, 20])
length_param = TimeVaryingParameter([10, 1], [60])

while s.beat < 65:
    fork(play_gesture, args=(center_pitch_param(), width_param(), length_param()), initial_tempo=180)
    wait_for_children_to_finish()
