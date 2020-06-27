"""
SCAMP Example: Note Properties

Shows how the fourth (optional) properties argument to "play_note" can be used to affect other aspects of playback and
notation, such as articulation and noteheads. All properties are ultimately converted into a NotePropertiesDictionary;
If a string is given, it is parsed into key / value pairs. In many cases, e.g. with "staccato" below, SCAMP can infer
that it is referring to an articulation.
"""


from scamp import *

s = Session()
s.fast_forward_in_beats(float("inf"))

piano = s.new_part("piano")

s.start_transcribing()

# passing comma-separated key value pairs
piano.play_note(60, 0.5, 1, "notehead: x, articulation: staccato")
# just a value; articulation type inferred
piano.play_note(60, 0.5, 1, "staccato")
# "play_chord" can take multiple noteheads separated by slashes
piano.play_chord([60, 65], 0.5, 1, "noteheads: x/circle-x")
# passing a dictionary also possible
piano.play_note(60, 0.5, 1, {
    "articulations": ["tenuto", "accent"],
})
performance = s.stop_transcribing()


def test_results():
    return (
        performance,
        performance.to_score()
    )
