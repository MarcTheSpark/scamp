"""
SCAMP Example: Key Plane

Maps the computer keyboard onto a 2D grid of pitches with scamp_extensions' KeyPlane; each key press
starts a flute note whose pitch and volume come from its row and column.
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

from scamp_extensions.interaction import KeyPlane
from scamp_extensions.utilities import remap
from scamp import *

s = Session()

flute = s.new_part("flute")

notes = {}


def callback(coordinates, press_or_release, modifiers):
    if press_or_release == "press":
        print("Press at:", coordinates, "with modifiers", modifiers)
        notes[coordinates] = flute.start_note(remap(coordinates[0], 60, 96, 0, 1), remap(coordinates[1], 0.3, 1, 0, 1))
    else:
        print("Release at:", coordinates, "with modifiers", modifiers)
        if notes[coordinates]:
            notes[coordinates].end()


KeyPlane(callback, normalize_coordinates=True).start(blocking=True, suppress=True)
