"""
SCAMP Example: Generating Notation

Plays a simple C Major arpeggio, and generates notation for it.
"""

from scamp import *

s = Session()
s.fast_forward_in_beats(float("inf"))
violin = s.new_part("Violin")

# begin recording (defaults to transcribing all instruments within the session)
s.start_transcribing()
for pitch in [60, 64, 67, 72]:
    violin.play_note(pitch, 1, 0.5)
    # stop the recording and save the recorded
    # note events as a performance

# a Performance is essentially a note event list representing exactly
# when and how notes were played back, in continuous time
performance = s.stop_transcribing()


def test_results():
    return (
        performance,
        performance.to_score()
    )
