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

def _adjust_beat_at_time(self, time_to_adjust, desired_beat):
    # first off, how much does the beat need to change
    delta_beat = desired_beat - current_beat_at_adjust_point
    # once we squish the adjustable_segments so that they take (desired_beat - start_beat) beats,  how much will
    # we have to adjust the curvature to make back the time we lost?
    proportional_time_change_needed = (current_beat_at_adjust_point - start_beat) / (desired_beat - start_beat)

    # now, how much leeway do we actually have by adjusting curvature
    segment_time_ranges = [segment.get_integral_range() for segment in adjustable_segments]
    # range of how long the entire thing could take
    total_time_range = (sum(x[0] for x in segment_time_ranges), sum(x[1] for x in segment_time_ranges))
    # how each segment currently takes
    segment_times = [segment.integrate_segment(segment.start_time, segment.end_time)
                     for segment in adjustable_segments]
    # how long all the segments take
    total_time = sum(segment_times)

    # check if it's even possible to get to make up the time by simply adjusting curvatures
    if not total_time_range[0] / total_time < proportional_time_change_needed < total_time_range[1] / total_time:
        # if not return false, and go back to the backup segments (before we interpolated some points)
        self.segments = back_up
        return False

    # if we're here, it's possible.
