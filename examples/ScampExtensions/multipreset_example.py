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
from scamp_extensions.playback import MultiPresetInstrument

s = Session(tempo=90)

# This sets up a new viola instrument within Session s that can do arco, pizzicato and harmonic playback
# the first line creates the instrument using Session s and names it "viola".
# we can then add presets to the instrument, giving each preset a name, a ScampInstrument or soundfont preset to use,
# and properties/notations that get bundled with the notes when that preset is used.
# `bundled_properties` get attached to every note played by a preset
# `bundled_properties_on_switch` get attached to the first note played by a preset when we switch to it
# `bundled_properties_on_switch_away` get attached to the next note when we switch away from a preset. This is usually
# a "cancelling" notation, like "arco" after a section of "pizz"
viola = MultiPresetInstrument(s, "Viola").\
    add_preset("arco", "viola").\
    add_preset("pizz", "pizzicato", bundled_properties_on_switch="text: pizz",
               bundled_properties_on_switch_away="text: arco").\
    add_preset("harmonic", "bowed glass", bundled_properties="notehead: harmonic, pitch + 12")

s.start_transcribing()

# when playing notes/chords, the MultiPresetInstrument has an extra `preset` argument that can be used to specify
# the desired preset to use.
viola.play_note(60, 1, 2)
viola.play_note(55, 1, 1, preset="pizz")
viola.play_note(67, 1, 1.5, preset="harmonic")
viola.play_note(68, 1, 0.5, preset="pizz")
viola.play_note(67, 1, 0.5, preset="pizz")
viola.play_note(65, 1, 0.5, preset="pizz")
viola.play_note(63, 1, 1)
viola.play_note(62, 1, 1)
viola.play_note(67, 1, 1, preset="harmonic")
note_handle = viola.start_note(60, 1.0)
note_handle.change_pitch(67, 3)
wait(3)
note_handle.end()
note_handle = viola.start_note(67, 1.0, preset="pizz")
note_handle.change_pitch(60, 1)
wait(1)
note_handle.end()
note_handle = viola.start_note(60, 1.0, preset="pizz")
note_handle.change_pitch(67, 1)
wait(1)
note_handle.end()
note_handle = viola.play_note(67, 1.0, 1.0, preset="harmonic")

viola.play_note(60, 1, 3)

s.stop_transcribing().to_score(time_signature="3/4").show()


