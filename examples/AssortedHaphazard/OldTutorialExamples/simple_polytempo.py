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

trumpet = s.new_part("trumpet")
trombone = s.new_part("trombone")


def trumpet_part(clock: Clock):
    while s.beat() < 3:
        trumpet.play_note(67, 1, 0.5)
    clock.set_rate_target(0.5, 6, duration_units="time")
    while s.beat() < 12:
        trumpet.play_note(67, 1, 0.5)


s.set_tempo_target(100, 9)
trumpet_clock = s.fork(trumpet_part)
trombone_based_performance = s.start_transcribing()
trumpet_based_performance = s.start_transcribing(clock=trumpet_clock)

while s.beat() < 12:
    trombone.play_note(60, 1, 1)

s.stop_transcribing(trombone_based_performance)
s.stop_transcribing(trumpet_based_performance)

trombone_based_performance.to_score("3/4", title="Trombone Clock").show_xml()
trumpet_based_performance.to_score("3/4", title="Trumpet Clock").show_xml()