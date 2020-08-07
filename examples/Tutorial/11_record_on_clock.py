"""
SCAMP Example: Record on Clock

Same as previous example, except that the performance is recorded from the point of view of the
trumpet part, resulting in the same sound notated in reference to a different changing tempo curve.
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

from scamp import *
s = Session()

trumpet = s.new_part("trumpet")
trombone = s.new_part("trombone")


# When a function is forked, it is run on
# a child clock of the process forking it.
# This child clock can be passed as the
# first argument and then manipulated.
def trumpet_part(clock: Clock):
    # play eighth notes for three beats
    while s.beat() < 3:
        trumpet.play_note(67, 1, 0.5)

    # tell the clock for this child process
    # to slow down to 1/2 speed over six
    # beats in the parent process
    # metric_phase_target of 0 ensures that
    # we reach that we land perfectly on a beat
    clock.set_rate_target(0.5, 6, duration_units="time",
                          metric_phase_target=0)

    # keep playing eighth notes until 12
    # beats pass in the parent session
    while s.beat() < 12:
        trumpet.play_note(67, 1, 0.5)


# Have the session as a whole speed up to
# 100 BPM over the first nine beats
s.set_tempo_target(100, 9)
# fork returns the Clock associated
# with the newly forked process
trumpet_clock = s.fork(trumpet_part)
s.start_transcribing(clock=trumpet_clock)
# Play quarter notes for 12 beats
while s.beat() < 12:
    trombone.play_note(60, 1, 1)

# Stop recording and show the result
performance = s.stop_transcribing()
performance.to_score(time_signature="3/4").show()
