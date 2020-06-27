"""
SCAMP Example: Glissando from Envelope

Plays a glissando by passing an Envelope to the pitch parameter of play_note.
"""

from scamp import *

s = Session()
s.fast_forward_in_beats(float("inf"))

viola = s.new_part("viola")

e = Envelope.from_levels_and_durations(
    [60, 72, 66, 70], [3, 1, 1],
    curve_shapes=[2, -2, -2]
)

s.start_transcribing()

viola.play_note(e, 1.0, 4)

performance = s.stop_transcribing()


def test_results():
    return (
        performance,
        performance.to_score()
    )
