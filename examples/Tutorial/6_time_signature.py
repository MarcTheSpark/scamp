"""
SCAMP Example: Time Signatures

Plays a simple C Major arpeggio, and generates notation for it in three different ways:
    - with a 3/8 time signature
    - with a 3/8 time signature for the first measure followed by 2/4
    - with alternating 3/8 and 2/4 time signatures
    - with a list of bar lengths determining time signatures
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

from scamp import *

s = Session()
violin = s.new_part("Violin")

# begin recording (defaults to transcribing
# all instruments within the session)
s.start_transcribing()
for _ in range(4):
    for pitch in [60, 64, 67, 72]:
        violin.play_note(pitch, 1, 0.5)
        # stop the recording and save the recorded
        # note events as a performance

performance = s.stop_transcribing()
# quantize and convert the performance to a Score object and open it as a PDF,
# this time imposing a time signature of 3/8
performance.to_score(time_signature="3/8").show()

# a list is interpreted as a (non-repeating) sequence of time signatures
performance.to_score(time_signature=["3/8", "2/4"]).show()

# if a repeating sequence of time signatures is desires, end the list with "loop"
performance.to_score(time_signature=["3/8", "2/4", "loop"]).show()

# Alternatively, bar line locations can be given and sensible time signatures will be selected
performance.to_score(bar_line_locations=[1.5, 3.5, 8]).show()
