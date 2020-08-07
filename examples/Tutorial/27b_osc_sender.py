"""
SCAMP Example: OSC Sender

This doesn't really use SCAMP; it is merely a python script that sends out a few choice osc messages of the sort that
27a_osc_listener.py is designed to respond to.
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

from pythonosc import udp_client
import time


client = udp_client.SimpleUDPClient("127.0.0.1", 5995)

# play a chromatic scale on the piano
for x in range(65, 85):
    client.send_message("/play_note/piano", [x, 0.5, 0.1])
    time.sleep(0.1)

# play a horrifying bagpipe cluster
client.send_message("/play_bagpipe_cluster", [])
time.sleep(0.5)

# play a chromatic scale on the flute
for x in range(65, 85):
    client.send_message("/play_note/flute", [x, 0.5, 0.1])
    time.sleep(0.1)

# play another horrifying bagpipe cluster
client.send_message("/play_bagpipe_cluster", [])
time.sleep(0.5)

# play a chromatic scale alternating between flute and piano
for x in range(65, 85):
    client.send_message("/play_note/" + ("flute", "piano")[x % 2], [x, 0.5, 0.1])
    time.sleep(0.1)
