"""
SCAMP Example: Playback Implementations

Shows how to create parts that use different implementations for playback. This just shows the setup code;
it doesn't really do anything.
"""

from scamp import *

s = Session()
# Calling "new_part" results in a default SoundfontPlaybackImplementation, and
# add_streaming_midi_playback gives this a MIDIStreamPlaybackImplementation as well
# (here, port 2 is used for output)
piano = s.new_part("piano").add_streaming_midi_playback(2)
# Calling "new_osc_part" gives the instrument an OSCPlaybackImplementation
synth = s.new_osc_part("synth", ip_address="127.0.0.1", port=57120)
# Calling "new_silent_part" results in an instrument with no PlaybackImplementation
silent = s.new_silent_part("silent")
