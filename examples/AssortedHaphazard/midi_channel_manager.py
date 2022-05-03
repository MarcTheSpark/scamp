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
from scamp._midi import MIDIChannelManager
import time

mcm = MIDIChannelManager(5)
print("A", mcm.assign_note_to_channel(101, 64, 0, {}))  # channel 0: 101
time.sleep(1)
print("B", mcm.assign_note_to_channel(102, 70, 0, {}))  # channel 0: 101, 102
time.sleep(0.3)
mcm.end_note(101)  # channel 0: 102
print("C", mcm.assign_note_to_channel(103, 79, "variable", "variable"))  # channel 1 (variable): 103
print("D", mcm.assign_note_to_channel(104, 72, 0.5, {}))  # channel 2 (pitch bend 0.5): 104
print("D2", mcm.assign_note_to_channel(105, 72, 0, {}))  # channel 0: 102, 105
mcm.end_note(102)  # channel 0: 105
print("E", mcm.assign_note_to_channel(106, 72, 0.5, {}))  # channel 3 (conflicting pitch): 106
time.sleep(0.5)
mcm.end_note(105)  # channel 0: empty, but should need ring time
time.sleep(0.6)
print("F", mcm.assign_note_to_channel(107, 72, 0.5, {}))  # channel 0
