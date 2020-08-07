"""
SCAMP Example: Start and End Note

Plays notes by calling start_note (or start_chord) and then manipulating them afterward, instead of defining the course
of the note from the beginning with "play_note". The "start_note" and "start_chord" functions return handles that can
be used to change the pitch, volume or other parameters of the note after they have started, as well as end the note.
"""

#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  SCAMP (Suite for Computer-Assisted Music in Python)                                           #
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

violin = s.new_part("violin")

s.start_transcribing()

# start a violin note on middle C with volume 1
note_handle1 = violin.start_note(60, 1.0)
wait(1)
# after 1 second, start a chord on Bb4 / D5 / F#5 with volume 1
note_handle2 = violin.start_chord([70, 74, 78], 1.0)
# change the pitch of the first note to F#3, glissing over the course of 2 seconds
note_handle1.change_pitch(54, 2.0)
wait(1)
# one second later, start changing the pitch of the chord so that its first note (the Bb4) glisses up to E5
# over the course of one second. The other notes of the chord will move in parallel to Ab5 and C6.
note_handle2.change_pitch(76, 1.0)
wait(2)
# after 2 seconds, end the first note and start a fade out to volume 0 over the course of 2 seconds on the chord.
note_handle1.end()
note_handle2.change_volume(0, 2)
# wait 2 seconds and then end the second chord
wait(2)
note_handle2.end()

s.stop_transcribing().to_score().show()
