"""
SCAMP Example: Scales

Demo of the scamp_extensions Scale object, a highly flexible representation of a scale that can be indexed into
infinitely in both directions from a root note. Scales can be microtonal (and even loaded from a scala file), and are
constructed from intervals that can be expressed as either a frequency ratio, a distance in cents, or a combination
of the two. Scales can also be transposed and modally rotated.
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
from scamp_extensions.pitch import Scale, ScaleType
from fractions import Fraction

s = Session(tempo=100)

clarinet = s.new_part("clarinet")

scales = {
    "C blues": Scale.from_pitches([48, 51, 53, 54, 55, 58, 60]),
    "Bb locrian": Scale.locrian(58),
    "Microtonal example 1": Scale(ScaleType(26., 104., Fraction(3, 2), (600., Fraction(5, 4)), 2, (204., 2)), 55),
    "C whole-half Octatonic": Scale.from_pitches([48, 50, 51]),
    "C half-whole Octatonic": Scale.octatonic(48, whole_step_first=False),  # different means of construction
    "C Melodic Minor": Scale.melodic_minor(48),
    "D Acoustic": Scale.melodic_minor(50, modal_shift=3),  # the "acoustic" scale is a mode of the melodic minor
    "Overtone Series": Scale(ScaleType(*(Fraction(n, 1) for n in range(2, 32))), 40, cycle=False),
    "Microtonal example 2:": Scale.from_start_pitch_and_cent_or_ratio_intervals(
        55, ["200.", "5/4", "200., 5/4", "3/2", "7/4", "2"]),
    "Bohlen Pierce from Scala File": Scale.from_scala_file("bohlen_12.scl", 48)
}

scales["Bohlen Pierce Transposed"] = scales["Bohlen Pierce from Scala File"].transposed(7)

for scale_name, scale in scales.items():
    print("Playing notes of the {} scale.".format(scale_name))
    for scale_degree in range(0, 16):
        clarinet.play_note(scale[scale_degree], 1.0, 0.25)

    print("Playing chords from the {} scale.".format(scale_name))
    for scale_degree in range(0, 16):
        clarinet.play_chord(scale[list(range(scale_degree, scale_degree + 5, 2))], 1.0, 0.25)
