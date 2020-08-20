"""
SCAMP Example: Blocking False

Demonstrating the ability to have non-blocking calls to play_note. This plays two notes that each last
for two beats, but overlapping by one beat.
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

# import the scamp namespace
from scamp import *
# construct a session object
s = Session()
# add a new violin part to the session
violin = s.new_part("Violin")

# start playing a 2-beat C, but return immediately
violin.play_note(60, 1, 2, blocking=False)
# wait for only one beat
wait(1)
# start playing a 2-beat E, blocking this time
violin.play_note(64, 1, 2)
