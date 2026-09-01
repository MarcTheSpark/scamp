"""
SCAMP Example: Octave Lines

A short passage of random notes for violin and piano, which uses the optional note properties argument to `play_note`
to apply ottava when notes are very high or very low.

Tags: notation/spanners, time/clocks
"""

from scamp import *
import random

# makes output deterministic; comment out for variation
random.seed(42)

s = Session()

s.tempo = 70

violin = s.new_part("violin")
piano = s.new_part("piano")

s.start_transcribing()

def violin_part():
    while s.beat < 16:
        pitch = random.randint(80, 105)
        ottava_mark = "15va" if pitch > 98 else "8va" if pitch > 90 else None
        violin.play_note(pitch, 0.5, 0.25, ottava_mark)


def piano_part():
    while s.beat < 16:
        pitch = random.randint(25, 45)
        ottava_mark = "8vb" if pitch < 32 else None
        piano.play_note(pitch, 0.5, 0.5, ["staccato", ottava_mark])
        wait(random.choice([0, 0.5, 1.0]))


fork(violin_part)
fork(piano_part)
wait_for_children_to_finish()

perf = s.stop_transcribing()
perf.to_score().show()
