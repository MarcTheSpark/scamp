"""
SCAMP Example: Save a Performance

Saves an Ensemble and a recorded Performance to JSON, for the load_and_play_performance example.

Tags: save and load, transcription
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
import math


s = Session()

shaku = s.new_part("shakuhachi")
oboe = s.new_part("oboe")


def oboe_part():
    while True:
        oboe.play_note(75 + random.random() * 7 + 15 * math.sin(get_beat() / 10), 0.4, 0.25)


def shaku_part():
    pentatonic = [0, 2, 4, 7, 9]
    while True:
        if random.random() < 0.5:
            shaku.play_note(66 + random.choice(pentatonic) + 12*random.randint(0, 2),
                            Envelope([1.0, 0.2, 1.0, 1.0], [0.15, 0.85, 0.15], [0, 2, 0]),
                            2.5, blocking=True)
            wait(0.5 + random.choice([0, 0.5]))
        else:
            shaku.play_note(66 + random.choice(pentatonic) + 12*random.randint(0, 2), 1.0, 0.2*(1+random.random()*0.3))
            wait(random.choice([1, 2, 3]))


s.fork(oboe_part)
s.fork(shaku_part)

s.set_tempo_target(300, Moment.after_time(30))

s.wait(15)
s.start_transcribing()
print("Starting transcription...")
s.wait(15)
performance = s.stop_transcribing()
print("Stopped transcribing. Saving transcription.")

performance.save_to_json("perfShakoboe.json")

s.wait_forever()
