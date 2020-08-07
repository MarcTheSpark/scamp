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
from scamp_extensions.pitch import Scale
from definitions import *
from formal_parameters import *
from random import random, choice, uniform, seed

seed(0)
s = Session()

cello = s.new_part("cello")
pianoteq = s.new_midi_part("pianoteq", midi_output_device="IAC")
supercollider_instrument = s.new_osc_part("superInst", 57120, "127.0.0.1")

s.set_tempo_targets([150, 60], [TOTAL_LENGTH * 0.618, TOTAL_LENGTH],
                    duration_units="time")

s.start_transcribing()

interval = 1
cello_pitch = 48


def pianoteq_upbeat(clock: Clock):
    start_pitch = 72 + cello_pitch % 12
    end_pitch = 72 + (cello_pitch + interval) % 12
    if end_pitch < start_pitch:
        end_pitch += 12
    for i, p in enumerate([start_pitch + uniform(-k, k) for k in range(7)]):
        pianoteq.play_note(p, 0.3 + 0.1 * i, 0.5/7)
    
    clock.set_rate_target(pianoteq_gesture_rit_factor.value_at(s.time()), 15)
    p = end_pitch
    volume = 1.0
    pianoteq.play_note(p, volume, 0.375)
    for _ in range(int(pianoteq_gesture_length.value_at(s.time()))):
        scale = Scale.from_pitches([cello_pitch + x for x in (0, 2, 3, 5, 6, 8, 9, 11, 12)])
        degree = round(scale.pitch_to_degree(p))
        pianoteq.play_note(scale.degree_to_pitch(degree - 4), volume, 0.125)
        pianoteq.play_note(scale.degree_to_pitch(degree - 3), volume, 0.375)
        volume *= 0.8
        p = scale.degree_to_pitch(degree - 3)
        

def pianoteq_filler(clock: Clock):
    p = 60
    while random() < pianoteq_filler_probability.value_at(s.time()):
        scale = Scale.from_pitches([cello_pitch + x for x in (0, 2, 3, 5, 6, 8, 9, 11, 12)])
        degree = round(scale.pitch_to_degree(p))
        if p == 60:
            wait(1/5)
        for i in range(4):
            pianoteq.play_chord([scale.degree_to_pitch(degree + 2*i),
                                 scale.degree_to_pitch(degree + 2*i + 3)],
                                0.6 + 0.1*i, 1/5, "staccatissimo")
        if p != 60 and random() < pianoteq_filler_probability.value_at(s.time()):
            pianoteq.play_chord([scale.degree_to_pitch(degree + 4),
                                 scale.degree_to_pitch(degree + 9),
                                 scale.degree_to_pitch(degree + 11)],
                                1.0, 1/5, "staccatissimo")
        else:
            wait(1/5)
        p = wrap_in_range(p + 6, 62, 92)


def sc_gesture(start_pitch):
    start_pan = uniform(-1, 1)
    end_pan = uniform(0, 1) if start_pan < 0 else uniform(-1, 0)
    register_ref = sc_register.value_at(s.time())
    supercollider_instrument.play_note(
        register_ref + cello_pitch % 12,
        [0, 0.5], sc_gesture_length.value_at(s.time()),
        {"crackliness_param": [0, crackliness.value_at(s.time())],
         "pan_param": start_pan}
    )
    supercollider_instrument.play_note(
        [register_ref + cello_pitch % 12, register_ref + cello_pitch % 12 + 12],
        [[0.5, 0], [1], [-4]], sc_gesture_length.value_at(s.time()) * 3/2,
        {"crackliness_param": [crackliness.value_at(s.time()), 0],
         "spread_param": [[0, 0, 0.5], [0.5, 0.5]],
         "pan_param": end_pan}
    )


piano_tech_clock = None
sc_gesture_clock = None

while True:
    if random() < cello_continue_probability.value_at(s.time()):
        if len(bar_lines) > 0 and s.beat() - bar_lines[-1] > 3 and \
                (piano_tech_clock is None or not piano_tech_clock.alive):
            piano_tech_clock = s.fork(pianoteq_filler)
            do_bar_line(s.beat())
            
        cello.play_note(cello_pitch, forte_piano, choice([1.0, 1.5]))
    else:
        # end condition; break and go to final note
        if cello_pitch % 12 == 0 and s.time() >= TOTAL_LENGTH:
            break
        if s.time() > 20 and (sc_gesture_clock is None or not sc_gesture_clock.alive):
            sc_gesture_clock = s.fork(sc_gesture)
        cello.play_note(cello_pitch, diminuendo, choice([2.0, 2.5, 3.0]))
        if piano_tech_clock is not None:
            piano_tech_clock.kill()
        wait(choice([0.5, 1.0]))
        if s.time() > 40:
            piano_tech_clock = s.fork(pianoteq_upbeat)
        
        if random() < cello_staccato_probability.value_at(s.time()):
            cello_pitch = wrap_in_range(cello_pitch + interval, 36, 60)
            interval += 1
            wait(0.25)
            cello.play_note(cello_pitch, 0.9, 0.25, "staccato")
        else:
            wait(0.5)
        do_bar_line(s.beat())
        
    cello_pitch = wrap_in_range(cello_pitch + interval, 36, 60)
    interval += 1
    
cello.play_note(36, diminuendo, [4.0])
do_bar_line(s.beat())

s.stop_transcribing().to_score(bar_line_locations=bar_lines, max_divisor=14).show()
