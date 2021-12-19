"""
SCAMP Example: Ornaments, tremolo and other single-note notations. These notational details are passed to the fourth,
optional "properties" argument of play_note.
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

# these lines set an playback adjustment to occur on notes with the "turn" notation, bending the pitch up and down
# a similar approach could be taken with other notations.
turn_pitch_envelope = Envelope([0, 0, 1, 1, 0, 0, -1, -1, 0, 0], [0.07, 0, 0.07, 0, 0.07, 0, 0.07, 0, 0.07])
playback_settings.set_playback_adjustment("turn", NotePlaybackAdjustment.add_to_params(pitch=turn_pitch_envelope))

s = Session()
violin = s.new_part("Violin")
s.start_transcribing()

for pitch in [60, 64, 67, 72]:
    violin.play_note(pitch, 1, 0.5)

violin.play_note(74, 1, 1, "tremolo")
violin.play_note(75, 1, 0.5, "tremolo1")
violin.play_note(76, 1, 0.25, "tremolo2")
violin.play_note(78, 1, 0.25, "tremolo3")
violin.play_note(77, 1, 1.75, "turn, tremolo, fermata")
violin.play_note(84, 1, 0.25, "mordent")
violin.play_note(83, 1, 1, "inverted mordent")
violin.play_note(82, 1, 1, "trill mark")
violin.play_note(81, 1, 1, "open-string")
violin.play_note(80, 1, 1, "up-bow")
violin.play_note(79, 1, 1, "down-bow")
violin.play_note(78, 1, 1, "stopped")
violin.play_note(77, 1, 1, "snap-pizzicato")

violin.play_chord([60, 64, 67, 72], 1, 1, "arpeggiate")
violin.play_chord([60, 64, 67, 72], 1, 1, "arpeggiate down")
violin.play_chord([60, 64, 67, 72], 1, 1, "fermata, arpeggiate up")

performance = s.stop_transcribing()
performance.to_score().show()
