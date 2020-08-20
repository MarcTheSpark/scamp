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

from scamp import Ensemble


def construct_ensemble():
    global piano, flute, strings, ensemble
    ensemble = Ensemble()

    ensemble.print_default_soundfont_presets()

    piano = ensemble.new_part("piano")
    flute = ensemble.new_part("flute")
    strings = ensemble.new_part("strings", (0, 40))


def play_some_stuff():
    while True:
        piano.play_note(65, 0.5, 1.0)
        flute.play_note(70, 0.5, 0.25)
        strings.play_note([75, 73], 0.5, 1.0, blocking=True)


construct_ensemble()

# # ------- Use this line to save the Ensemble so that it can be reloaded -------
# ensemble.save_to_json("SavedFiles/savedEnsemble.json")

# # ------- Use this line to reloaded the Ensemble from the saved file -------
# ensemble = Ensemble.load_from_json("SavedFiles/savedEnsemble.json")
# piano, flute, strings = ensemble.instruments

play_some_stuff()
