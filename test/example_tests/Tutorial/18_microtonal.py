"""
SCAMP Example: Microtonal Playback and Notation

Plays a few microtonal chords and notates them, turning on exact microtonal annotations.
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
s.fast_forward_in_beats(float("inf"))

piano = s.new_part("piano")

s.start_transcribing()

# this causes the true pitches to be written into the score by the notes, as midi pitch values.
engraving_settings.show_microtonal_annotations = True
# playing microtonal pitches is as simple as using floating-point values for pitch
piano.play_chord([62.7, 71.3], 1.0, 1)
piano.play_chord([65.2, 70.9], 1.0, 1)
piano.play_chord([71.5, 74.3], 1.0, 1)

performance = s.stop_transcribing()


def test_results():
    return (
        performance,
        performance.to_score()
    )
