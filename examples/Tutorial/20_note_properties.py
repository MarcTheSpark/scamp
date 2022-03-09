"""
SCAMP Example: Note Properties

Shows how the fourth (optional) properties argument to "play_note" can be used to affect other aspects of playback and
notation, such as articulation and noteheads. All properties are ultimately converted into a NotePropertiesDictionary;
If a string is given, it is parsed into key / value pairs. In many cases, e.g. with "staccato" below, SCAMP can infer
that it is referring to an articulation.
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

# the properties argument can be used to specify which voice a note should appear in
# you can also add dynamic text, although it doesn't cause any change in playback within SCAMP
piano.play_note(62, 0.5, 0.5, "voice: 1, dynamic: ff")
piano.play_note(60, 0.5, 0.5, "voice: 2")
piano.play_note(58, 0.5, 0.5, "voice: 2")
piano.play_note(62, 0.5, 0.5, "voice: 2")
piano.play_note(64, 0.5, 0.5, "voice: 1")
piano.play_note(62, 0.5, 0.5, "voice: 2")
piano.play_note(60, 0.5, 0.5, "voice: 2")
piano.play_note(64, 0.5, 0.5, "voice: 2")

# You can also specify voices by name instead of number. In this case, scamp will
# simply keep notes in the same named voice together, determining the number automatically
piano.play_note(62, 0.5, 0.5, "voice: top_notes, dynamic: pp")
piano.play_note(60, 0.5, 0.5, "voice: bottom_notes")
piano.play_note(58, 0.5, 0.5, "voice: bottom_notes")
piano.play_note(62, 0.5, 0.5, "voice: bottom_notes")
piano.play_note(64, 0.5, 0.5, "voice: top_notes")
piano.play_note(62, 0.5, 0.5, "voice: bottom_notes")
piano.play_note(60, 0.5, 0.5, "voice: bottom_notes")
piano.play_note(64, 0.5, 0.5, "voice: bottom_notes")

# You can also use the properties argument for playback adjustments, which do not affect notation
# This will cut the length of the note in half, and play it up an octave
piano.play_note(65, 0.5, 1, "playback_adjustment: length * 0.5, pitch + 12")
# Usually it's not necessary to specify that it's a playback adjustment.
# This will play the note with a gliss up and down a half step
piano.play_note(65, 0.5, 1, "pitch + [0, 2, 0]")
# This will change the playback length to two beats, but still notate a quarter note
# The result is that the note bleeds into the following beat (potentially good for legato)
piano.play_note(65, 0.5, 1, "length = 2")
# Internally all of these strings are converted to a NotePlaybackAdjustment object, which you can give directly
# This sets the note to play back with a totally different pitch volume and duration than notated
piano.play_note(65, 0.5, 1, NotePlaybackAdjustment.set_params(pitch=78, volume=0.9, length=0.1))

# Under the hood, everything we pass to the properties argument gets converted to a NoteProperties object
# We can actually create our own NoteProperties objects, which bundle together several properties, perhaps with
# a specified playback adjustment. Then, we can pass this to the properties argument of play_note. Here, we create
# the wiggle property, which puts a mordent and the italic word "ZIG" on a note, and makes it bend up and down.
wiggle = NoteProperties([
    "text: *ZIG*",
    "notation: inverted mordent",
    NotePlaybackAdjustment.add_to_params(pitch=Envelope([0, 1, 0], [0.1, 0.1]))
])
piano.play_note(62, 0.5, 0.5, wiggle)
piano.play_note(64, 0.5, 0.5, "staccato")
piano.play_note(65, 0.5, 0.5, [wiggle, "staccato"])
piano.play_note(63, 0.5, 0.5, "staccato")
piano.play_note(66, 0.5, 2, [wiggle, "accent"])

s.stop_transcribing().to_score().show()
