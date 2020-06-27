"""
SCAMP Example: Microtonal Playback and Notation

Plays a few microtonal chords and notates them, turning on exact microtonal annotations.
"""

from scamp import *

s = Session()
s.fast_forward_in_beats(float("inf"))

piano = s.new_part("piano")

s.start_transcribing()

# this causes the true pitches to be written into the score by the notes, as midi pitch values.
engraving_settings.show_microtonal_annotations = True
# playing microtonal pitches is as simple as using floating-point values for pitch
piano.play_chord([62.7, 71.3], 1.0, 1)
piano.play_chord([65.2, 70.9], 1.0, 1)
piano.play_chord([71.5, 74.3], 1.0, 1)

performance = s.stop_transcribing()


def test_results():
    return (
        performance,
        performance.to_score()
    )
