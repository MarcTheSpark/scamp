"""
SCAMP Example: Multiple Tempos

Three wind parts on independent looping and functional tempo envelopes.
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
from math import sin
import random

s = Session()

flute = s.new_part("flute")
clarinet = s.new_part("clarinet")
bassoon = s.new_part("bassoon")


def flute_part():
    # looping tempo shapes now live on apply_tempo_envelope rather than set_tempo_targets(..., loop=True)
    tempo_env = TempoEnvelope.from_levels_and_durations(
        (160, 160, 100, 100, 130, 130, 70, 70), (1, 0, 1, 0, 1, 0, 1))
    apply_tempo_envelope(tempo_env, loop=True)
    while True:
        flute.play_note(int(70 + 10 * get_rate()), 0.8, 0.25, "staccato")


def clarinet_part():
    apply_tempo_function(lambda t: 60 + 30 * sin(t), duration_units="time")
    while True:
        clarinet.play_note(int(65 + (get_rate() - 1) * 20 + random.random() * 8), 0.8, 0.25, "staccato")


def bassoon_part():
    apply_tempo_function(lambda t: 80 + 40 * sin(t / 3), duration_units="time")
    while True:
        bassoon.play_chord([40, 44, 50], 0.8, 0.5, "staccatissimo")


flute_clock = s.fork(flute_part, name="Flute")
clarinet_clock = s.fork(clarinet_part, name="Clarinet")
bassoon_clock = s.fork(bassoon_part, name="Bassoon")


performance1 = s.start_transcribing(clock=flute_clock)
performance2 = s.start_transcribing(clock=clarinet_clock)
performance3 = s.start_transcribing(clock=bassoon_clock)

s.wait(30)
s.kill()
s.stop_transcribing(performance1).quantized().to_score(title="Recorded on flute clock").show()
s.stop_transcribing(performance2).quantized().to_score(title="Recorded on clarinet clock").show()
s.stop_transcribing(performance3).quantized().to_score(title="Recorded on bassoon clock").show()
