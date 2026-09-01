"""
SCAMP Example: Multiple Voices with Octave Lines

Same as the voices example, but with ottava applied to certain voices. These ottava contradict one another when the
voices are (by default) placed on the same staff, so the largest octave line wins and a warning is emitted. To avoid
this conflict, set `engraving_settings.max_voices_per_staff = 1` to place each voice in a separate staff.

Tags: notation/properties, notation/engraving, notation/spanners
"""

from scamp import *

s = Session()

piano = s.new_part("piano")

melody = (
    (0, 0.5), (3, 1/2 + 1/3), (2, 1/3), (5, 1/3), (3, 0.5), (None, 1.0), (5, 0.25), (6, 0.75), (7, 0.5)
)


def _do_melody(start_pitch, dilation_factor=1.0, properties=None):
    """Play the melody at a given pitch and speed, passing along the given properties to every note."""
    for interval, dur in melody:
        piano.play_note(start_pitch + interval if interval is not None else None,
                        0.7,
                        dur * dilation_factor,
                        properties)


def fork_melody(start_pitch, dilation_factor=1.0, properties=None):
    fork(_do_melody, args=(start_pitch, dilation_factor, properties))


s.start_transcribing()

fork_melody(70, properties=["8va", "voice: A"])
wait(2)
fork_melody(97, 2, properties=["15va", "voice: B"])
wait(4)
fork_melody(67, properties="voice: C")
wait(2)
fork_melody(35, 0.5, properties=["8vb", "voice: 4"])
wait_for_children_to_finish()

perf = s.stop_transcribing()

# default: allow 4 voices per staff, resulting in conflicting octave lines; largest displacement wins
perf.to_score(title="Awful version: 4 voices with conflicting octave lines in one staff.").show()

# use this setting to force each voice onto its own staff to avoid conflicting octave lines
engraving_settings.max_voices_per_staff = 1
perf.to_score(title="Using `engraving_settings.max_voices_per_staff = 1`").show()
