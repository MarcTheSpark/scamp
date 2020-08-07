"""
SCAMP Example: Random Durations and Rests

Loops a C major arpeggio twice, but with random, floating-point durations.
Also sometimes adds a rest of up to a second between notes.
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

# import the scamp namespace
from scamp import *
# import the random module from
# the python standard library
import random
random.seed(0)

# construct a session object
s = Session()
s.fast_forward_in_beats(float("inf"))

# add a new violin part to the session
violin = s.new_part("Violin")

for _ in range(2):  # loop twice
    for pitch in [60, 64, 67, 72]:
        # pick a duration between 0.5 to 1.5
        dur = random.uniform(0.5, 1.5)
        # play a note of that duration
        violin.play_note(pitch, 1, dur)
        # with probability of one half, wait for between 0 and 1 seconds
        if random.random() < 0.5:
            # note that "wait" is the same here as "s.wait". What "wait" does it find the
            # clock operating on the given thread and call wait on that. In this case, that
            # clock is the Session as a whole.
            wait(random.random())


def test_results():
    return [True]