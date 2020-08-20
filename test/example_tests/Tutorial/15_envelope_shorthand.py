"""
SCAMP Example: Envelope Shorthand

Plays two glissandi by passing lists instead of envelopes to the pitch argument of play_note.
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

s.start_transcribing()

# a list of values results in evenly spaced glissando
viola.play_note([60, 70, 55], 1.0, 4)

# a list of lists can give values, durations, and (optionally) curve shapes
# this results in segment durations of 2 and 1 and curve shapes of -2 and 0
viola.play_note([[60, 70, 55], [2, 1], [-2, 0]], 1.0, 4)


performance = s.stop_transcribing()


def test_results():
    return (
        performance,
        performance.to_score()
    )
