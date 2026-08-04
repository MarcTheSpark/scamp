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
from scamp_extensions.process import LSystem

s = Session()
s.tempo = 100


perc1 = s.new_part("Perc. 1", preset="power")
perc2 = s.new_part("Perc. 2", preset="power")
perc3 = s.new_part("Perc. 3", preset="power")


l_syst1 = LSystem(
    "a",
    {
        "a": "c b",
        "b": "bac",
        "c": " aa"
    },
    {
        " ": None,
        "a": 56,
        "b": 60,
        "c": 81,
    }
)

l_syst2 = LSystem(
    "b",
    {
        "a": "c b",
        "b": "bac",
        "c": " aa"
    },
    {
        " ": None,
        "a": 50,
        "b": 67,
        "c": 63,
    }
)

l_syst3 = LSystem(
    "c",
    {
        "a": "c b",
        "b": "bac",
        "c": " aa"
    },
    {
        " ": None,
        "a": 70,
        "b": 75,
        "c": 82,
    }
)


def play_notes(instrument, pitches, volume, duration):
    for pitch in pitches:
        instrument.play_note(pitch, volume, duration)


for generation in range(6):
    print(f"Generation {generation}:")
    print(f"  Part 1: {l_syst1.get_generation(generation)}")
    print(f"  Part 2: {l_syst2.get_generation(generation)}")
    print(f"  Part 3: {l_syst3.get_generation(generation)}")
    fork(play_notes, args=(perc1, l_syst1.get_generation_meanings(generation), 0.8, 0.25))
    fork(play_notes, args=(perc2, l_syst2.get_generation_meanings(generation), 0.8, 0.25))
    fork(play_notes, args=(perc3, l_syst3.get_generation_meanings(generation), 0.8, 0.25))
    wait_for_children_to_finish()
    wait(2)
