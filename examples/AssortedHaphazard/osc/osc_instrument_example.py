"""
Uses an OSCPlaycorderInstrument to send messages to a running SuperCollider script at OSCListenerPython.scd
To test out, run all the code blocks in OSCListenerPython.scd, make sure that the port below matches the
result of NetAddr.langPort, and then run this script.
"""

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

from scamp import *
import random


session = Session()

# The port here must match the result of NetAddr.langPort in SuperCollider
fm_sines = session.new_osc_part("fm_sines", 57120)
hihat = session.new_osc_part("hihat", 57120)


def fm_sines_part():
    while True:
        fm_sines.play_note([random.random() * 20 + 60, random.random() * 20 + 60],
                           [[1, 0], [1], [-2]], random.random() * 3 + 0.3,
                           {"fm_param": [random.random() * 30, random.random() * 30]},
                           blocking=False)
        wait(random.random() * 3)


def hihat_part():
    while True:
        hihat.play_note(80 + random.random() * 40, random.random(), 0.25)


session.fork(fm_sines_part)
session.fork(hihat_part)
session.wait_forever()


