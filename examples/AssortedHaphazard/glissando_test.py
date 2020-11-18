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

piano = session.new_part("piano")
piano.set_max_pitch_bend(20)

random.seed(1)

session.start_transcribing()

while session.time() < 12:
    gliss = Envelope(
        [random.random() * 20 + 60, random.random() * 20 + 60, random.random() * 20 + 60, random.random() * 20 + 60],
        [random.random()+0.5, random.random()+0.5, random.random()+0.5]
    )

    if random.random() < 0.5:
        piano.play_note(gliss, 1.0, random.random()*2 + 0.5)
    else:
        piano.play_chord([gliss, gliss+4], 1.0, random.random()*2 + 0.5)
    if random.random() < 0.5:
        session.wait(random.random() * 2)

# # Thia line causes the turn-around points of the glissandi to be rendered differently
# engraving_settings.glissandi.control_point_policy = "grace"
performance = session.stop_transcribing()

performance.quantize(QuantizationScheme.from_time_signature("5/4"))
performance.save_to_json("SavedFiles/quantized_glisses.json")

session.wait(2)
print("playing quantized")
performance.play(clock=session)

performance.to_score().show()
