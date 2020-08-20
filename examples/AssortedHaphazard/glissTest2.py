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
import random

session = Session()

piano = session.new_part("violin")

random.seed(1)

session.start_transcribing()

piano.play_note([60, 70, 50, 65, 55, 62, 58, 60], 1.0, 4.0)
piano.play_chord([[60, 70, 50, 65, 55, 62, 58, 60], [67, 77, 57, 72, 62, 69, 65, 67]], 1.0, 4.0)

performance = session.stop_transcribing()
engraving_settings.glissandi.inner_grace_relevance_threshold = 0
engraving_settings.glissandi.control_point_policy = "grace"
performance.to_score().show()
