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

from scamp import Session
import random
from pynput.keyboard import Listener

rate = 1


def on_press(key):
    try:
        global rate
        rate = 1 + int(str(key).replace("\'", ""))
        print("New rate is ", rate)
    except ValueError:
        # ignore key presses that don't correspond to number keys
        pass


# Collect events until released
Listener(on_press=on_press).start()


s = Session()

piano = s.new_part("piano", num_channels=40)


def do_chords(clock):
    while True:
        if rate != clock.rate:
            clock.rate = rate
        piano.play_chord([random.random()*24 + 60, random.random()*24 + 60], 1.0, 1.0)


def do_fast_notes(clock):
    while True:
        if rate != clock.rate:
            clock.rate = rate
        piano.play_note(random.random()*24 + 80, 1.0, 0.5)


s.fork(do_chords)
s.fork(do_fast_notes)
s.wait_forever()
