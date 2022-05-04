"""
SCAMP EXAMPLE: Spanners

Demonstration of starting and stopping various spanners, such as slurs, hairpins, trills, brackets, and pedal lines.
Note that there is some finickiness with both lilypond and MusicXML output. LilyPond does not allow multiple of the
same spanner at the same time (at least in the same voice), whereas MusicXML does. If exporting to MusicXML, you can
keep the spanners straight by providing a label.

On the other hand, implementations of MusicXML in many notation programs mangle spanner input. So there's that.
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
piano = s.new_part("Piano")

s.start_transcribing()


def violin_part():
    # the easiest way to create spanners is with string shorthand: start/stop + the spanner type + addition attributes
    # Note: abjad/lilypond only allows two levels of slur: regular slurs and phrasing slurs. MusicXML allows more.
    # In order to clarify which spanner you're refering to when there are multiple of the same type, you can give
    # the spanner a label starting with a hash, like this: "start slur #1" or "start hairpin > #HARRY"
    violin.play_note(61, 0.7, 1/3, "start slur, start phrasing slur, start bracket dashed 'intensely'")
    violin.play_note(62, 0.7, 1/3)
    violin.play_note(64, 0.7, 1/3, "stop slur")
    # you can also pass a spanner start or stop object directly
    violin.play_note(61, 0.7, 1/3, StartSlur())
    violin.play_note(62, 0.7, 1/3)
    violin.play_note(64, 0.7, 1/3, StopSlur())
    # hairpin types can be ">" "<", as well as ">o" "o<" for niente hairpins
    violin.play_note(65, 0.7, 1/3, "start slur, start hairpin <")
    violin.play_note(64, 0.7, 1/3)
    violin.play_note(62, 0.7, 1/3, "stop slur")
    violin.play_note(65, 0.7, 1/3, "start slur")
    violin.play_note(64, 0.7, 1/3)
    violin.play_note(62, 0.7, 1/3, "stop bracket, stop slur")
    violin.play_note(67, 0.7, 2, "f, start trill flat")
    violin.play_note(65, 0.7, 1)
    violin.play_note(64, 0.7, 1, "stop phrasing slur, stop trill")


def piano_part():
    piano.play_note(33, 0.7, 0.5, "start pedal, start dashes 'cresc.'")
    piano.play_note(45, 0.7, 0.5)
    piano.play_note(52, 0.7, 0.5)
    piano.play_note(57, 0.7, 0.5)
    piano.play_note(38, 0.7, 0.5, "change pedal")
    piano.play_note(50, 0.7, 0.5)
    piano.play_note(53, 0.7, 0.5)
    piano.play_note(57, 0.7, 0.5, "stop dashes")
    piano.play_chord([43, 50, 58], 0.7, 2, "arpeggiate, stop pedal, f, start hairpin >")
    piano.play_chord([45, 49, 57], 0.7, 2, "arpeggiate, stop hairpin, fermata")


fork(piano_part)
violin_part()
performance = s.stop_transcribing()


def test_results():
    return (
        performance,
        performance.to_score()
    )
