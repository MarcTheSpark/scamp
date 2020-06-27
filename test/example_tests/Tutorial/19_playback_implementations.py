"""
SCAMP Example: Playback Implementations

Shows how to create parts that use different implementations for playback. This assumes that you are connecting to
a midi device on port zero.
"""

from scamp import *

s = Session()
s.fast_forward_in_beats(float("inf"))

# Calling "new_part" results in a default SoundfontPlaybackImplementation, and
# add_streaming_midi_playback gives this a MIDIStreamPlaybackImplementation as well
# (here, port 0 is used for output)
piano = s.new_part("piano").add_streaming_midi_playback(0)
# Calling "new_osc_part" gives the instrument an OSCPlaybackImplementation
# This one is set up to communicate with the supercollider instrument in the osc_to_supercollider.scd example
synth = s.new_osc_part("vibrato", ip_address="127.0.0.1", port=57120)
# Calling "new_silent_part" results in an instrument with no PlaybackImplementation
silent = s.new_silent_part("silent")

s.start_transcribing()

for _ in range(4):
    piano.play_note(60, 1, 0.5)
    synth.play_note(62, 1, 0.5)
    silent.play_note(63, 1, 0.5)

performance = s.stop_transcribing()


def test_results():
    return (
        performance,
        performance.to_score(time_signature="6/8")
    )
