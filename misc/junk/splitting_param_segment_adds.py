if other.start_time == self.start_time and other.end_time == self.end_time:
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

self_delta = self.end_level - self.start_level
    other_delta = other.end_level - other.start_level
    try:
        norm_t_derivative_zero = -math.log(
            (other_delta * other.curve_shape - other_delta *
             other.curve_shape * math.exp(self.curve_shape)) /
            (self_delta * (math.exp(other.curve_shape) - 1) * self.curve_shape)
        ) / (other.curve_shape - self.curve_shape)
        if not 0 < norm_t_derivative_zero < 1:
            raise ValueError("Min/max out of range")
        # we'll break our segment at this point, since it's a local min or maximum
        break_point = self.start_time + norm_t_derivative_zero * (self.end_time - self.start_time)
        break_level = self.value_at(break_point) + other.value_at(break_point)
        part_1_halfway_time = (break_point + self.start_time) / 2
        part_1_halfway_level = self.value_at(part_1_halfway_time) + other.value_at(part_1_halfway_time)
        part_2_halfway_time = (break_point + self.end_time) / 2
        part_2_halfway_level = self.value_at(part_2_halfway_time) + other.value_at(part_2_halfway_time)
        segment_1 = ParameterCurveSegment.from_endpoints_and_halfway_level(
            self.start_time, break_point,
            self.start_level + other.start_level, break_level,
            self.value_at(part_1_halfway_level) + other.value_at(part_1_halfway_level)
        )
        segment_2 = ParameterCurveSegment.from_endpoints_and_halfway_level(
            break_point, self.end_time,
            break_level, self.end_level + other.end_level,
            self.value_at(part_2_halfway_level) + other.value_at(part_2_halfway_level)
        )
        return ParameterCurve([segment_1, segment_2])
    except ValueError:
        # this is either a domain error that happens when there is no point where the derivative is zero
        # or the error we raised in the case that that point is not within the range of this segment
        # in either case, just try to match the segment as best as possible
        halfway_time = self.start_time + (self.end_time - self.start_time) / 2
        return ParameterCurveSegment.from_endpoints_and_halfway_level(
            self.start_time, self.end_time,
            self.start_level + other.start_level, self.end_level + other.end_level,
            self.value_at(halfway_time) + other.value_at(halfway_time)
        )
else:
    raise ValueError("ParameterCurveSegments can only be added if they have the same time range.")