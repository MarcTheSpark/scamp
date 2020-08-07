"""
SCAMP Example: OSC Listener

Sets up an osc listener using Session.register_osc_listener, which takes in OSC messages and plays back notes and
horrific bagpipe cluster. To run this example, first run this script, and then run 27b_osc_sender.py, which sends
messages to trigger playback. (Of course, the real value of this is that incoming OSC messages can come from anywhere
and can therefore be used to modify an ongoing SCAMP process.)
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

s = Session()
piano = s.new_part("piano")
flute = s.new_part("flute")
bagpipe = s.new_part("bagpipe")


def play_note_callback(osc_address, pitch, volume, length):
    if osc_address.split("/")[-1] == "piano":
        piano.play_note(pitch, volume, length, blocking=False)
    elif osc_address.split("/")[-1] == "flute":
        flute.play_note(pitch, volume, length, blocking=False)


def bagpipe_callback(osc_address):
    bagpipe.play_chord([70, 71, 72, 73, 74, 75, 76], 0.5, 0.2, blocking=False)


s.register_osc_listener(5995, "/play_note/*", play_note_callback)
s.register_osc_listener(5995, "/play_bagpipe_cluster", bagpipe_callback)


s.wait_forever()
