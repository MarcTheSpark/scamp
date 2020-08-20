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

session = Session()
piano = session.new_part("piano")

session.start_transcribing()

for _ in range(2):
    piano.play_note(65, 0.5, 1.25, "accent")
    piano.play_note(67, 0.5, 0.25, "staccato")
    piano.play_note(68, 0.5, 1.25, "staccato")
    piano.play_note(70, 0.5, 0.25, "staccato")
    piano.play_note(72, 0.5, 0.25, "staccatissimo, marcato")
    piano.play_note(70, 0.5, 0.25, "staccato")
    piano.play_note(68, 0.5, 0.25, "staccato")
    piano.play_note(67, 0.5, 0.25, "staccato")

piano.play_chord([65, 77], 0.5, 2, "tenuto")

session.stop_transcribing().to_score().show()
