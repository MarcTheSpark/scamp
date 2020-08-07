"""
SCAMP Example: Envelopes (advanced)

A more comprehensive list of ways to construct and modify Envelopes.

"""

#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  SCAMP (Suite for Computer-Assisted Music in Python)                                           #
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

from scamp import Envelope
import math

# Ways of constructing Envelopes

envelope_from_levels = Envelope.from_levels((1.0, 0.2, 0.6, 0), length=3)

envelope_from_levels_and_durations = Envelope.from_levels_and_durations((1.0, 0.2, 0.6, 0), (2.0, 1.0, 3.0))

envelope_from_levels_and_durations_with_curve_shapes = Envelope.from_levels_and_durations(
    (1.0, 0.2, 0.6, 0), (2.0, 1.0, 3.0), curve_shapes=(2, 2, -3)
)

envelope_from_points = Envelope.from_points((-1, 5), (1, 6), (5, -2))

envelope_from_points_with_curve_shapes = Envelope.from_points((-1, 5, -3), (1, 6, 2), (5, -2))

envelope_from_list1 = Envelope.from_list([3, 6, 2, 0])  # just levels

envelope_from_list2 = Envelope.from_list([[3, 6, 2, 0], 7])  # levels and total duration

envelope_from_list3 = Envelope.from_list([[3, 6, 2, 0], [2, 0.5, 5]])  # levels and segment durations

envelope_from_list4 = Envelope.from_list([[3, 6, 2, 0], [2, 0.5, 5], [3, 0, -3]])  # levels, durations and curve shapes

envelope_from_function = Envelope.from_function(lambda x: math.sin(x), -2, 7)

release_envelope = Envelope.release(3, curve_shape=-2)

attack_release_envelope = Envelope.ar(0.1, 2, release_shape=-3)

attack_sustain_release_envelope = Envelope.asr(1, 0.8, 4, 2, attack_shape=-4)

adsr_envelope = Envelope.adsr(0.2, 1.0, 0.3, 0.7, 3.0, 1.0, decay_shape=-2, release_shape=3)

# Arithmetic with Envelopes:
# Approximates as best as possible the result of function addition / multiplication / division
# Since the resulting functions are often not piecewise exponential, we break the result apart at local min / max
# and points of inflection and try to fit exponentials to each of the resulting segments

a = Envelope.adsr(0.2, 1.0, 0.3, 0.7, 3.0, 1.0, decay_shape=-2, release_shape=3)
b = Envelope.adsr(0.2, 1.0, 0.3, 0.7, 3.0, 1.0, decay_shape=-2, release_shape=3).shift_horizontal(3) + 1

envelope_from_points_with_curve_shapes.append_envelope(envelope_from_function)

attack_sustain_release_envelope.prepend_envelope(envelope_from_function)


def test_results():
    return [
        envelope_from_levels.json_dumps(),
        envelope_from_levels_and_durations.json_dumps(),
        envelope_from_levels_and_durations_with_curve_shapes.json_dumps(),
        envelope_from_points.json_dumps(),
        envelope_from_points_with_curve_shapes.json_dumps(),
        envelope_from_list1.json_dumps(),
        envelope_from_list2.json_dumps(),
        envelope_from_list3.json_dumps(),
        envelope_from_list4.json_dumps(),
        envelope_from_function.json_dumps(),
        release_envelope.json_dumps(),
        attack_release_envelope.json_dumps(),
        attack_sustain_release_envelope.json_dumps(),
        adsr_envelope.json_dumps(),
        ((a + b) * (a - b)).json_dumps(),
        (a / b).json_dumps(),
        envelope_from_points_with_curve_shapes.json_dumps()
    ]