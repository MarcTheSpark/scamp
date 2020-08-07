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
import math

s = Session()
piano = s.new_part("piano")


def child(clock: Clock):
    clock.apply_tempo_function(lambda b: 90 + 60 * math.sin(b / 5))
    global grand_child_clock
    grand_child_clock = clock.fork(grand_child)
    while True:
        wait(1)


def grand_child(clock: Clock):
    clock.rate = 2
    while True:
        piano.play_note(103, 1, 1)
        piano.play_note(103, 1, 1)
        piano.play_note(103, 1, 1)
        piano.play_note(103, 1, 1)
        clock.rate = 1 / clock.rate


def play_wiggle(p, transposition=0):
    for _ in range(2):
        piano.play_note(p + transposition, 0.5, 0.25)
        piano.play_note(p+1 + transposition, 0.5, 0.25)
        piano.play_note(p + transposition, 0.5, 0.25)
        piano.play_note(p-1 + transposition, 0.5, 0.25)


def key_down(name, number):
    if 20 < number < 110:
        grand_child_clock.fork(play_wiggle, args=(number, ))


grand_child_clock = None
child_clock = s.fork(child)
s.register_keyboard_listener(on_press=key_down, suppress=True)

while True:
    piano.play_note(108, 1.0, 1)
    s.wait(1)
