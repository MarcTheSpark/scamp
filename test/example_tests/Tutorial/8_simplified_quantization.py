"""
SCAMP Example: Simplified Quantization

Same as last example except that a restriction on the max beat divisor is
imposed on the quantization, rendering simpler -- if somewhat less accurate -- results.
"""

from scamp import *
import random

s = Session()
s.fast_forward_in_beats(float("inf"))

violin = s.new_part("Violin")

# begin recording
s.start_transcribing()

for _ in range(2):  # loop twice
    for pitch in [60, 64, 67, 72]:
        dur = random.uniform(0.5, 1.5)
        violin.play_note(pitch, 1, dur)
        if random.random() < 0.5:
            # note that "wait" is the same here as "s.wait". What "wait" does it find the
            # clock operating on the given thread and call wait on that. In this case, that
            # clock is the Session as a whole.
            wait(random.random())

performance = s.stop_transcribing()


def test_results():
    return (
        performance,
        performance.to_score(time_signature="3/4", title="Default Quantization"),
        performance.to_score(time_signature="3/4", max_divisor=4, title="Max Divisor of 4"),
        performance.to_score(time_signature="3/4", simplicity_preference=3, title="Strong Simplicity Preference")
    )
