"""
SCAMP Example: Time Signatures

Plays a simple C Major arpeggio, and generates notation for it in three different ways:
    - with a 3/8 time signature
    - with a 3/8 time signature for the first measure followed by 2/4
    - with alternating 3/8 and 2/4 time signatures
    - with a list of bar lengths determining time signatures
"""

from scamp import *

s = Session()
s.fast_forward_in_beats(float("inf"))
violin = s.new_part("Violin")

# begin recording (defaults to transcribing
# all instruments within the session)
s.start_transcribing()
for _ in range(4):
    for pitch in [60, 64, 67, 72]:
        violin.play_note(pitch, 1, 0.5)
        # stop the recording and save the recorded
        # note events as a performance

performance = s.stop_transcribing()


def test_results():
    return (
        performance,
        performance.to_score(time_signature="3/8"),
        performance.to_score(time_signature=["3/8", "2/4"]),
        performance.to_score(time_signature=["3/8", "2/4", "loop"]),
        performance.to_score(bar_line_locations=[1.5, 3.5, 8])
    )
