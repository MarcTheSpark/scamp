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

import abjad

measure = abjad.Container()
tuplet = abjad.Tuplet((4, 5))
measure.extend(r"\times 4/5 { c'4 r16 } r4 f'2")
abjad.attach(abjad.LilyPondLiteral(r"\stemless"), measure[-1])
# print(format(measure))
# abjad.show(measure)
score = abjad.Score([measure])


file_definitions = "% Definitions to improve score readability\n" \
               "stemless = {\n" \
               "    \once \override Beam.stencil = ##f\n" \
               "    \once \override Flag.stencil = ##f\n" \
               "    \once \override Stem.stencil = ##f\n" \
               "}"

score_overrides = "% improve glissando appearance and readability" \
                 "\override Score.Glissando.minimum-length = #4\n" \
                 "\override Score.Glissando.springs-and-rods = #ly:spanner::set-spacing-rods\n" \
                 "\override Score.Glissando.thickness = #2\n" \
                 "\override Score.Glissando #'breakable = ##t"

abjad.attach(abjad.LilyPondLiteral(score_overrides), score)

lilypond_file = abjad.LilyPondFile.new(
    music=score,
    default_paper_size=('a5', 'portrait'),
    global_staff_size=16,
)

# lilypond_file.items.insert(-1, file_definitions)
abjad.attach(file_definitions, lilypond_file)
print(format(lilypond_file))
abjad.show(lilypond_file)
