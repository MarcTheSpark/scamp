"""
SCAMP Example: Quantization of Random Floating-Point Durations

Similar to the "Random Durations and Rests" example, except that now we generate
notation. Since the lengths are floating point, quantization occurs in the call to "to_score"
"""

from scamp import *
import random

s = Session()
violin = s.new_part("Violin")

# begin recording
s.start_recording()

for _ in range(2):  # loop twice
    for pitch in [60, 64, 67, 72]:
        dur = random.uniform(0.5, 1.5)
        violin.play_note(pitch, 1, dur)
        if random.random() < 0.5:
            # note that "wait" is the same here as "s.wait". What "wait" does it find the
            # clock operating on the given thread and call wait on that. In this case, that
            # clock is the Session as a whole.
            wait(random.random())

performance = s.stop_recording()

# quantize and convert the score in 3/4
performance.to_score("3/4").show()
