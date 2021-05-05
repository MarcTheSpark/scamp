"""
SCAMP Example: Double Score

Records two performances, turns them into scores, renders to abjad, and sticks them together!
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
import abjad
from scamp import *
import random

# one way of setting an initial tempo
s = Session(tempo=100)
s.fast_forward_in_beats(float("inf"))

oboe = s.new_part("oboe")
bassoon = s.new_part("bassoon")


# define a function for the oboe part
def oboe_part():
    # play random notes until we have
    # passed beat 7 in the session
    end_beat = s.beat() + 8
    while s.beat() < end_beat - 1:
        pitch = int(random.uniform(67, 79))
        volume = random.uniform(0.5, 1)
        length = random.uniform(0.25, 1)
        oboe.play_note(pitch, volume, length)
    # end with a note of exactly the right
    # length to take us to the end of beat 8
    oboe.play_note(80, 1.0, end_beat - s.beat())


# define a function for the bassoon part
def bassoon_part():
    # simply play quarter notes on random
    # pitches for 8 beats
    end_beat = s.beat() + 8
    while s.beat() < end_beat:
        bassoon.play_note(
            random.randint(52, 59), 1, 1
        )


s.start_transcribing()
# start the oboe and bassoon parts as two parallel child processes
s.fork(oboe_part)
s.fork(bassoon_part)
# have the session wait for the child processes to finish (return)
s.wait_for_children_to_finish()
performance = s.stop_transcribing()
score1 = performance.to_score()

performance2 = s.start_transcribing()
# start the oboe and bassoon parts as two parallel child processes
s.fork(oboe_part)
s.fork(bassoon_part)
# have the session wait for the child processes to finish (return)
s.wait_for_children_to_finish()
s.stop_transcribing()
score2 = performance2.to_score()

score1_block = abjad.Block(name="score")
score1_block.items.append(score1.to_abjad(wrap_as_file=False))

score2_block = abjad.Block(name="score")
score2_block.items.append(score2.to_abjad(wrap_as_file=False))

lilypond_file = abjad.LilyPondFile(items=[score1_block, score2_block])


def test_results():
    return (
        performance,
        performance2,
        score1,
        score2,
        abjad.lilypond(lilypond_file)
    )
