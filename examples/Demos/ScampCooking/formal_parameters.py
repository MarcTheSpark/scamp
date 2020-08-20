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

TOTAL_LENGTH = 180

# golden ratio durations
gr, one_minus_gr = TOTAL_LENGTH * 0.618, TOTAL_LENGTH * (1 - 0.618)

cello_continue_probability = Envelope.from_levels_and_durations([0.4, 1.0, 0], [gr, one_minus_gr])
cello_staccato_probability = Envelope.from_levels([0, 1], length=TOTAL_LENGTH)
pianoteq_gesture_length = Envelope.from_levels([0, 0, 10, 0], length=TOTAL_LENGTH)
pianoteq_gesture_rit_factor = Envelope.from_levels_and_durations([0.25, 0.8, 0.1], [gr, one_minus_gr])
pianoteq_filler_probability = Envelope.from_levels_and_durations([0.3, 0.97, 0.3], [gr, one_minus_gr])
crackliness = Envelope.from_levels_and_durations([0.6, 1.0, 0], [gr, one_minus_gr])
sc_gesture_length = Envelope.from_levels_and_durations([5, 2, 5], [gr, one_minus_gr])
sc_register = Envelope.from_levels_and_durations([72, 72, 60, 60, 48, 48, 36, 36 ],
                                                 [TOTAL_LENGTH * 0.7, 0, TOTAL_LENGTH * 0.1, 0, TOTAL_LENGTH * 0.1, 0, TOTAL_LENGTH * 0.1])


if __name__ == "__main__":
    cello_continue_probability.show_plot("Cello continue probability")
    cello_staccato_probability.show_plot("Cello staccato probability")
    pianoteq_gesture_length.show_plot("Pianoteq gesture length")
    pianoteq_gesture_rit_factor.show_plot("Pianoteq rit factor")
    pianoteq_filler_probability.show_plot("Pianoteq filler probability")
    crackliness.show_plot("SC instrument crackliness")
    sc_gesture_length.show_plot("SC instrument gesture length")
    sc_register.show_plot("SC instrument register")
