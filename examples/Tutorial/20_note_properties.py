"""
SCAMP Example: Note Properties

Shows how the fourth (optional) properties argument to "play_note" can be used to affect other aspects of playback and
notation, such as articulation and noteheads. All properties are ultimately converted into a NotePropertiesDictionary;
If a string is given, it is parsed into key / value pairs. In many cases, e.g. with "staccato" below, SCAMP can infer
that it is referring to an articulation.
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
piano = s.new_part("piano")

s.start_transcribing()

# passing comma-separated key value pairs
piano.play_note(60, 0.5, 1, "notehead: x, articulation: staccato")
# just a value; articulation type inferred
piano.play_note(60, 0.5, 1, "staccato")
# "play_chord" can take multiple noteheads separated by slashes
piano.play_chord([60, 65], 0.5, 1, "noteheads: x/circle-x")
# passing a dictionary also possible
piano.play_note(60, 0.5, 1, {
    "articulations": ["tenuto", "accent"],
})
s.stop_transcribing().to_score().show()
