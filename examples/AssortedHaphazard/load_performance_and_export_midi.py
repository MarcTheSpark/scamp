"""
To be run after "load_and_play_performance.py", since this loads up that performance as well as the Ensemble.
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

import random
from scamp import *


random.seed(0)
s = Session()
s.set_rate_target(2, 10, duration_units="time")
s.fast_forward_to_beat(float("inf"))
clar = s.new_part("clarinet")
piano = s.new_part("piano")

performance = s.start_transcribing()


def piano_part():
    while True:
        piano.play_note(random.randint(40, 58), random.uniform(0.3, 0.8), 0.5, "staccato")


fork(piano_part)

for p in [random.randint(50, 80) for _ in range(30)]:
    clar.play_note([p, p + 1, p - 2], Envelope([0.8, 0.1, 1.0], [0.1, 1.0]), random.uniform(0.1, 2),
                   f"param_10: {random.uniform(0, 1)}" if random.random() < 0.5 else "param_10: [0, 1]")

s.stop_transcribing().export_to_midi_file("midi_export.mid")