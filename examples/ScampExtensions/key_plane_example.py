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

piano = s.new_part("piano")


def callback(coordinates, press_or_release, modifiers):
    if press_or_release == "press":
        print("Press at:", coordinates, "with modifiers", modifiers)
        piano.play_note(remap(coordinates[0], 40, 80), remap(coordinates[1], 0.3, 1), 0.25, blocking=False)
    else:
        print("Release at:", coordinates, "with modifiers", modifiers)


KeyPlane(callback, normalize_coordinates=True).start(blocking=True, suppress=True)
