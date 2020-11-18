"""
SCAMP Example: Volume Envelope

Plots an envelope representing a forte-piano-crescendo dynamic, and then uses it to affect the dynamics of a note's
playback. This example shows that an Envelope can be passed to the volume argument of "play_note", just like it can
to the pitch argument. (The list short-hand also works, by the way.)
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
viola = s.new_part("viola")

fp_cresc = Envelope(
    [0.8, 0.3, 1],
    [0.07, 0.93],
    curve_shapes=[2, 4]
)

# plot the dynamic curve
fp_cresc.show_plot("fp cresc.")

# play a note with the dynamic curve
viola.play_note(48, fp_cresc, 4)
