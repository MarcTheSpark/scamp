"""
SCAMP Example: Generating Notation

Plays a simple C Major arpeggio, and generates notation for it.
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
s.fast_forward_in_beats(float("inf"))
violin = s.new_part("Violin")

# begin recording (defaults to transcribing all instruments within the session)
s.start_transcribing()
for pitch in [60, 64, 67, 72]:
    violin.play_note(pitch, 1, 0.5)
    # stop the recording and save the recorded
    # note events as a performance

# a Performance is essentially a note event list representing exactly
# when and how notes were played back, in continuous time
performance = s.stop_transcribing()


def test_results():
    return (
        performance,
        performance.to_score()
    )
