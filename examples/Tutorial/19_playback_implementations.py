"""
SCAMP Example: Playback Implementations

Shows how to create parts that use different implementations for playback. This assumes that you are connecting to
a midi device on port zero.
"""

#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  This file is part of SCAMP (Suite for Computer-Assisted Music in Python)                      #
#  Copyright © 2020 Marc Evanstein <marc@marcevanstein.com>.                                     #
#                                                                                                #
#  This program is free software: you can redistribute it and/or modify it under the terms of    #
#  the GNU General Public License as published by the Free Software Foundation, either version   #
#  3 of the License, or (at your option) any later version.                                      #
#                                                                                                #
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;     #
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     #
#  See the GNU General Public License for more details.                                          #
#                                                                                                #
#  You should have received a copy of the GNU General Public License along with this program.    #
#  If not, see <http://www.gnu.org/licenses/>.                                                   #
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #

from scamp import *

s = Session()
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

s.stop_transcribing().to_score(time_signature="6/8").show()
