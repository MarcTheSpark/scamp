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

s = Session(tempo=120)

violin = s.new_part("violin")
s.start_transcribing()

for _ in range(3):
    for p in [62, 65, 63, 67, 68, 72, 70]:
        violin.play_note(p, 0.7, 0.5, "key: Eb")

pymusicxml_score = s.stop_transcribing().to_score().to_music_xml()
pymusicxml_part = pymusicxml_score.contents[0]
pymusicxml_part.measures[0].key = "Eb"

pymusicxml_score.export_to_file("KeySig.musicxml")
