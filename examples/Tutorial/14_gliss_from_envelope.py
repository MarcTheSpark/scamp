"""
SCAMP Example: Glissando from Envelope

Plays a glissando by passing an Envelope to the pitch parameter of play_note.
"""

from scamp import *

s = Session()
viola = s.new_part("viola")

e = Envelope.from_levels_and_durations(
    [60, 72, 66, 70], [3, 1, 1],
    curve_shapes=[2, -2, -2]
)

s.start_recording()

viola.play_note(e, 1.0, 4)

s.stop_recording().to_score().show()
