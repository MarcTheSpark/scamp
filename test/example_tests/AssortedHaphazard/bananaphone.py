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
from random import random
import math

session = Session()
session.fast_forward_in_beats(float("inf"))

session.set_tempo_target(300, 20)

violin = session.new_part("violin")
violin2 = session.new_part("violin2")

bass_banjo = session.new_part("banjass", (0, 105))


def violins():
    while True:
        for x in range(4):
            violin.play_note([[67 + x, 76 + x, 71 + x], [0.1, 1.0]], [1, 0.2, 1], 1.0 + 2.0 * random(), blocking=False)
            wait(random())
            violin2.play_note([[79 + x, 88 + x, 83 + x], [0.1, 1.0]], [1, 0.2, 1], 1.0 + 2.0 * random())


def banjass():
    while True:
        pitch = 36 + random() * 5
        for _ in range(int(random() * 20 + 10)):
            bass_banjo.play_note(pitch, 1.0, 0.08)
            bass_banjo.play_note(pitch + 1, 1.0, 0.08)
            pitch += 0.4
        wait(random() * 1.5)


def sine_glisses(this_clock):
    freq = 0.2
    while True:
        violin.play_note([72 + 10 * math.sin(this_clock.beat() * freq * 2 * math.pi),
                          72 + 10 * math.sin((this_clock.beat() + 1.0) * freq * 2 * math.pi)],
                         1.0, 1.0)


session.fork(violins)
session.fork(banjass)
session.fork(sine_glisses)
session.start_transcribing()
session.wait(20)
violin.end_all_notes()
violin2.end_all_notes()
bass_banjo.end_all_notes()
performance = session.stop_transcribing()


def test_results():
    old_engraving_settings = engraving_settings.duplicate()
    engraving_settings.glissandi.control_point_policy = "grace"
    engraving_settings.ignore_empty_parts = False
    engraving_settings.max_voices_per_part = 1
    out = (
        performance,
        performance.to_score(time_signature="2/4")
    )
    engraving_settings.glissandi.control_point_policy = old_engraving_settings.glissandi.control_point_policy
    engraving_settings.ignore_empty_parts = old_engraving_settings.ignore_empty_parts
    engraving_settings.max_voices_per_part = old_engraving_settings.max_voices_per_part
    return out

