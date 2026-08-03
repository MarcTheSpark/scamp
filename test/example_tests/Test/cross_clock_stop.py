"""
Regression test: stopping a transcription from a different clock than the one being recorded.

The recorded clock plays one note and then naps in a long wait. The master stops the transcription
5 beats later, while that clock is still mid-wait. The extracted tempo envelope should span all 5
beats — the moment we stop, mapped into the recorded clock — not stop at beat 1 where the recorded
clock last woke. (stop_transcribing holds the scheduler and extracts out to "now".)
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
s.fast_forward()
piano = s.new_part("piano")


def part():
    piano.play_note(60, 1.0, 1)   # one 1-beat note, then a long nap
    wait(50)


clock = s.fork(part, name="recorded")
performance = s.start_transcribing(piano, clock=clock)
s.wait(5)                          # stop from the master while `clock` is still napping
performance = s.stop_transcribing(performance)


def test_results():
    return [round(performance.tempo_envelope.length(), 6)]
