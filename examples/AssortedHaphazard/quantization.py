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
from random import random, seed

session = Session()
drum = session.new_part("metronome", (0, 116))
piano = session.new_part("piano")

recording = True

seed(4)


def piano_part():
    while recording:
        if random() < 0.5:
            piano.play_note(50 + random()*20, 0.5, random() * 1.5)
        else:
            piano.play_chord([50 + random()*20, 50 + random()*20], 0.5, random() * 1.5)


session.fork(piano_part)

print("Making Recording...", end="")
session.start_transcribing()
for _ in range(8):
    drum.play_note(80, 1, 1)

recording = False
performance = session.stop_transcribing()
quantized_performance = performance.quantized(
    QuantizationScheme([MeasureQuantizationScheme.from_time_signature("4/4", max_divisor=5, max_indigestibility=3)])
)

print("Done")

while True:
    print("Replaying recording with quantization")
    session.wait(1)
    quantized_performance.play(clock=session)

    print("Replaying recording without quantization")
    session.wait(1)
    performance.play(clock=session)
