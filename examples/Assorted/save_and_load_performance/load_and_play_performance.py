"""
SCAMP Example: Load and Play a Performance

Loads the Ensemble and Performance saved by save_performance.py and plays the
performance back under a gradually accelerating tempo.

Tags: save and load, performance playback, tempo change
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

shaku = s.new_part("shakuhachi")
oboe = s.new_part("oboe")

recorded_performance = Performance.load_from_json("perfShakoboe.json")

s.tempo = 60
s.set_tempo_target(300, Moment.after_time(40))

while True:
    print("(Re)starting performance.")
    # by default, the performance plays on the currently active clock, forking all parts according to
    # the tempo envelope at recording time. So the acceleration inside the recording is compounded with
    # the gradual session-wide acceleration here.
    # also, by default, we use the currently active session for the instruments.
    recorded_performance.play()
