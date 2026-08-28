"""
SCAMP Example: Quantization Comparison

Records a loose piano improvisation against a metronome, then plays back the quantized version.

Tags: notation/quantization
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
import random


s = Session()

drum = s.new_part("metronome", (0, 116))
piano = s.new_part("piano")

s.start_transcribing()


recording = True

random.seed(4)


def piano_part():
    while recording:
        if random.random() < 0.5:
            piano.play_note(50 + random.random()*20, 0.5, random.random() * 1.5)
        else:
            piano.play_chord([50 + random.random()*20, 50 + random.random()*20], 0.5, random.random() * 1.5)


s.fork(piano_part)

print("Making Recording...", end="")
for _ in range(8):
    drum.play_note(80, 1, 1)

recording = False
performance = s.stop_transcribing()
quantized_performance = performance.quantized(
    QuantizationScheme([
        MeasureQuantizationScheme.from_time_signature("4/4", max_divisor=5, max_divisor_indigestibility=3)
    ])
)

print("Done")

while True:
    print("Replaying recording with quantization")
    wait(1)
    quantized_performance.play()

    print("Replaying recording without quantization")
    wait(1)
    performance.play()
