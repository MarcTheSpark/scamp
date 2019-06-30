"""
SCAMP Example: Multi-Part Music

Plays two coordinated but independent parallel parts, one for oboe and one for bassoon.
"""

from scamp import *
import random

# one way of setting an initial tempo
s = Session(tempo=100)

oboe = s.new_part("oboe")
bassoon = s.new_part("bassoon")


# define a function for the oboe part
def oboe_part():
    # play random notes until we have
    # passed beat 7 in the session
    while s.beats() < 7:
        pitch = int(random.uniform(67, 79))
        volume = random.uniform(0.5, 1)
        length = random.uniform(0.25, 1)
        oboe.play_note(pitch, volume, length)
    # end with a note of exactly the right
    # length to take us to the end of beat 8
    oboe.play_note(80, 1.0, 8 - s.beats())


# define a function for the bassoon part
def bassoon_part():
    # simply play quarter notes on random
    # pitches for 8 beats
    while s.beats() < 8:
        bassoon.play_note(
            random.randint(52, 59), 1, 1
        )


s.start_transcribing()
# start the oboe and bassoon parts as two parallel child processes
s.fork(oboe_part)
s.fork(bassoon_part)
# have the session wait for the child processes to finish (return)
s.wait_for_children_to_finish()
performance = s.stop_transcribing()
performance.to_score().show()
