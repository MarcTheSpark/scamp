"""
SCAMP Example: OSC to SuperCollider

Plays back notes by sending OSC messages to the corresponding SuperCollider process.
Start SuperCollider and run the code blocks in osc_to_supercollider.scd before running this script.
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
import random

s = Session()
s.fast_forward_in_beats(float("inf"))

# on the other end, an OSC receiver is setup to play notes that take vibrato and OSC messages as well as the usual
vib = s.new_osc_part("vibrato", 57120)

s.start_transcribing()

# any property entries starting or ending with "param" will be treated as extra playback parameters
while s.beat() < 20:
    note_length = random.uniform(0.3, 3)
    # glissando between three random values
    pitch_env = [random.randint(60, 82) for _ in range(3)]
    volume_env = random.choice([
        # percussive envelope
        Envelope.ar(0.1, note_length - 0.1),
        # fp crescendo envelope
        Envelope([1, 0.2, 1], [0.1, note_length - 0.1], curve_shapes=[-2, 3])
    ])
    vib_width_env = [random.uniform(0, 5) for _ in range(2)]
    vib_freq_env = [random.uniform(3, 13) for _ in range(2)]
    vib.play_note(
        pitch_env, volume_env, note_length,
        {"param_vibWidth": vib_width_env,
         "param_vibFreq": vib_freq_env},
        blocking=False
    )
    wait(random.uniform(0.5, 3))

while vib.num_notes_playing() > 0:
    wait(1)

performance = s.stop_transcribing()


def test_results():
    old_mvpp = engraving_settings.max_voices_per_part
    engraving_settings.max_voices_per_part = 1
    out = (
        performance,
        performance.to_score(max_divisor=6, simplicity_preference=3)
    )
    engraving_settings.max_voices_per_part = old_mvpp
    return out

