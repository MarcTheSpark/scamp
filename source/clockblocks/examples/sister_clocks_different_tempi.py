"""
Like sister_clocks_same_tempo.py, except that sister 2 is running at a tempo of 180, making it 3 times faster than
sister 1. As a result, it goes through beats more quickly.

Note that sister2 ends when its _time_ reaches 10. This is the same thing as saying when its parent reaches beat 10.
The time of a clock runs the same regardless of its rate, and it represents the inherited rate from its parent, and
from its parent's parent, etc.
"""

from clockblocks import *

master = Clock()


def sister1(my_clock):
    # sister 1 prints once per second for the first five seconds
    while my_clock.beats() < 5:
        print("Sister 1 at beat {}".format(my_clock.beats()))
        wait(1)


def sister2(my_clock):
    # sister 1 prints thrice per second for the first 10 seconds
    while my_clock.time() < 10:
        print("Sister 2 at beat {}".format(my_clock.beats()))
        wait(1)


master.fork(sister1)
master.fork(sister2, initial_tempo=180)
master.wait_for_children_to_finish()
