"""
SCAMP Example: Glissando from Envelope

Plays a glissando by passing an Envelope to the pitch parameter of play_note.
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

viola = s.new_part("viola")

e = Envelope(
    [60, 72, 66, 70], [3 * 4/5, 1 * 4/5, 1 * 4/5],
    curve_shapes=[2, -2, -2]
)

s.start_transcribing()

viola.play_note(e, 1.0, 4)

performance = s.stop_transcribing()

s.kill()


def test_results():
    return (
        performance,
        performance.to_score()
    )
