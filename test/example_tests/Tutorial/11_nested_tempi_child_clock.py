"""
SCAMP Example: Nested Tempi (Recorded on Child Clock)

Recorded from the forked child clock.
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
import itertools

s = Session()
s.fast_forward_in_beats(float("inf"))

trumpet = s.new_part("trumpet", default_spelling_policy="c phrygian")
trombone = s.new_part("trombone", default_spelling_policy="c phrygian", clef_preference="bass")

trumpet_note_pattern = itertools.cycle([67, 72, 67, 68])
trombone_note_pattern = itertools.cycle([60, 55, 48, 49, 48])


# A forked function runs on its own child clock, nested under the session that forked it.
def trumpet_part():
    # play the trumpet figure in eighth notes until the session reaches beat 3
    while s.beat < 3:
        trumpet.play_note(next(trumpet_note_pattern), 1, 0.5)

    # slow this child clock to half its current rate over the next 7 beats of the parent
    # note that this doesn't necessarily mean that we will land on the beat in this child clock
    # `align_to=MetricPhaseTarget(0)` is what ensures that that happens.
    set_rate_target(0.5, Moment.after_time(7), align_to=MetricPhaseTarget(0))

    # keep playing eighth notes until the session reaches beat 16
    while s.beat < 16:
        trumpet.play_note(next(trumpet_note_pattern), 1, 0.5)


# speed the whole session up to 100 BPM over its first 14 beats
s.set_tempo_target(100, Moment.after_beats(14))
# fork returns the child clock it created, which we hand to the transcriber below
trumpet_clock = s.fork(trumpet_part)
# transcribe from the trumpet clock's timeline, so the same music is notated against its tempo curve
s.start_transcribing(clock=trumpet_clock)

# play the trombone figure in quarter notes until the session reaches beat 16
while s.beat < 16:
    trombone.play_note(next(trombone_note_pattern), 1, 1)

# Stop recording and show the result
performance = s.stop_transcribing()


def test_results():
    return (
        performance,
        performance.to_score(time_signature="3/4")
    )
