"""
Scratch test of chained tempo targets and bar-line placement options.
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
# s.fast_forward_in_time(100)

engraving_settings.tempo.include_guide_marks = False

violin = s.new_part("violin")

s.set_tempo_target(100, Moment.after_beats(5))
s.set_tempo_target(135, Moment.after_beats(26/3), truncate=False)
s.set_tempo_target(135, Moment.after_beats(14), truncate=False)
s.set_tempo_target(40, Moment.after_beats(18), truncate=False)
s.set_tempo_target(100, Moment.after_beats(18), truncate=False)
s.set_tempo_target(89, Moment.after_beats(27), truncate=False)

s.start_transcribing()

while s.beat < 30:
    violin.play_note(70 + (s.beat * 3) % 7, 1.0, 0.25)

performance = s.stop_transcribing()

# performance.to_score(time_signature="5/8").print_lilypond(True)
bob = [1.5]
import random
while bob[-1] < 50:
    bob.append(bob[-1] + random.randint(1, 30) * 0.25)

print(bob)
performance.to_score(bar_line_locations=bob).print_lilypond(True)
performance.to_score(bar_line_locations=bob).show()
