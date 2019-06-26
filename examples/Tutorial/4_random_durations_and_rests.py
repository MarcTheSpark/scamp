"""
SCAMP Example: Random Durations and Rests

Loops a C major arpeggio, but with random, floating-point durations.
Also sometimes adds a rest of up to a second between notes.
"""

# import the scamp namespace
from scamp import *
# import the random module from
# the python standard library
import random

# construct a session object
s = Session()
# add a new violin part to the session
violin = s.new_part("Violin")

while True:  # loop forever
    for pitch in [60, 64, 67, 72]:
        # pick a duration between 0.5 to 1.5
        dur = random.uniform(0.5, 1.5)
        # play a note of that duration
        violin.play_note(pitch, 1, dur)
        # with probability of one half, wait for between 0 and 1 seconds
        if random.random() < 0.5:
            # note that "wait" is the same here as "s.wait". What "wait" does it find the
            # clock operating on the given thread and call wait on that. In this case, that
            # clock is the Session as a whole.
            wait(random.random())
