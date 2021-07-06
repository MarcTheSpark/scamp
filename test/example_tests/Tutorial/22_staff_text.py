"""
SCAMP Example: Staff Text

Demonstrates various ways of adding text annotations to notes that are played. Text is one of the various
notational details that can be passed to the fourth optional "properties" argument of play_note
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

violin = s.new_part("violin")
s.start_transcribing()

# the simplest way to add text is to place a "text: [string]" entry in the fourth properties argument
violin.play_note(81, 0.7, 2, "text: chillingly")
# you can also use a StaffText object, which is a little more customizable
violin.play_note(69, 0.5, 2, StaffText("cresc.", bold=True, placement="below"))
# if you want multiple texts for the same note, you can separate them by commas
violin.play_note(70, 0.5, 1, "text: soft, text: (with pathos)")
# if you want to italicise the text without bothering with a StaffText object, you
# can use a leading/trailing asterisk or underscore, following Markdown conventions
# (only works on the whole text; you can't italicise only part of the text, for now)
violin.play_note(71, 0.8, 1, "text: *louder*")
# you can also do bold using a double asterisk/underscore
violin.play_note(72, 0.9, 1.5, "text: **LOUD**")
violin.play_note(73, 0.9, 0.25)
# here we see that texts can be given as part of a properties dictionary, under the
# "texts" entry. Also note how three asterisks can be used for bold italic.
violin.play_chord([62, 74], 1.0, 4.25, {
    "articulation": "accent",
    "texts": ["***INSANELY LOUD***",  StaffText("(break something)", placement="below")]
})

performance = s.stop_transcribing()

s.kill()


def test_results():
    return (
        performance,
        performance.to_score()
    )
