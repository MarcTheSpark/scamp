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
from scamp_extensions.composers.barlicity import *
import random


threshold = 0
syncopation_chance = 0


def mouse_move(x, y):
    global threshold, syncopation_chance
    syncopation_chance = x
    threshold = y


s = Session()

s.register_mouse_listener(on_move=mouse_move, relative_coordinates=True)

drum = s.new_part("taiko", (0, 116), num_channels=150)
violin = s.new_part("violin")

indispensibilities = get_indispensability_array(((2, 3), 2, 3, (2, 3), (2, 3, 2), (3, 2, 3, 3)), True)  # (5, 7), (7, 11)

handle = None
pitch = None

while True:
    for indispensibility in indispensibilities:
        if indispensibility > 0.9:
            if handle is None:
                pitch = 65 + (1 - threshold) * 25
                handle = violin.start_note(pitch, 0.8)
            elif random.random() < 0.6:
                handle.end()
                handle = None
        elif handle is not None:
            handle.change_pitch(pitch + (1 - indispensibility) * random.uniform(-syncopation_chance * 15, syncopation_chance * 15), 0.15)

        if random.random() < syncopation_chance:
            indispensibility = 1 - indispensibility
        if indispensibility > threshold:
            drum.play_note(40 + int(80 * (1 - indispensibility)),
                           0.5 + 0.5 * (indispensibility - threshold) / (1 - threshold), 0.1)
        else:
            wait(0.1)
