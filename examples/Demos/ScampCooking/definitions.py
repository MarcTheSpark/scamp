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

# playback_settings.adjustments.set("staccato", "length * 0.3")

forte_piano = Envelope.from_levels_and_durations(
    [0.8, 0.4, 1.0], [0.2, 0.8], curve_shapes=[0, 3]
)

diminuendo = Envelope.from_levels([0.8, 0.3])


def wrap_in_range(value, low, high):
    return (value - low) % (high - low) + low


bar_lines = []


def do_bar_line(beat):
    beats_since_last_bar_line = beat - bar_lines[-1] if len(bar_lines) > 0 else beat
    if beats_since_last_bar_line % 1 == 0 and beats_since_last_bar_line < 5:
        bar_lengths = [beats_since_last_bar_line]
    else:
        num_bars_to_add = 2
        while beats_since_last_bar_line / num_bars_to_add > 4:
            num_bars_to_add += 1
        last_bar_length = round(beats_since_last_bar_line / num_bars_to_add)
        remaining_bars_length = beats_since_last_bar_line - last_bar_length
        if remaining_bars_length <= 5:
            bar_lengths = [remaining_bars_length, last_bar_length]
        else:
            first_bar_length = remaining_bars_length % 3 + 3 if remaining_bars_length % 3 < 2 else remaining_bars_length % 3
            bar_lengths = [first_bar_length] + [3] * int((remaining_bars_length - first_bar_length) / 3) + [last_bar_length]
    for bar_length in bar_lengths:
        bar_lines.append(bar_lines[-1] + bar_length if len(bar_lines) > 0 else bar_length)

