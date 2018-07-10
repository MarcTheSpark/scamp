"""
Uses an OSCPlaycorderInstrument to send messages to a running SuperCollider script at OSCListenerPython.scd
To test out, run all the code blocks in OSCListenerPython.scd, make sure that the port below matches the
result of NetAddr.langPort, and then run this script.
"""

from playcorder import *
import random


pc = Playcorder()

# The port here must match the result of NetAddr.langPort in SuperCollider
fm_sines = pc.add_osc_part(57120, name="fm_sines")
hihat = pc.add_osc_part(57120, name="hihat")


def fm_sines_part():
    while True:
        fm_sines.play_note([random.random() * 20 + 60, random.random() * 20 + 60],
                           [[1, 0], [1], [-2]], random.random() * 3 + 0.3,
                           {"qualities": {"fm": [random.random() * 30, random.random() * 30]}},
                           blocking=False)
        wait(random.random() * 3)


def hihat_part():
    while True:
        hihat.play_note(80 + random.random() * 40, random.random(), 0.25)


pc.fork(fm_sines_part)
pc.fork(hihat_part)
pc.wait_forever()


