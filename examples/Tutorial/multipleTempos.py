from scamp import *
from math import sin
import random

session = Session()

flute = session.add_midi_part("flute")
clarinet = session.add_midi_part("clarinet")
bassoon = session.add_midi_part("bassoon")


def flute_part(clock: Clock):
    clock.apply_tempo_envelope((160, 160, 100, 100, 130, 130, 70, 70), (1, 0, 1, 0, 1, 0, 1), loop=True)
    while True:
        flute.play_note(int(70 + 10 * clock.rate), 0.8, 0.25, "staccato")


def clarinet_part(clock: Clock):
    clock.apply_tempo_function(lambda t: 60 + 30 * sin(t), duration_units="time")
    while True:
        clarinet.play_note(int(65 + (clock.rate - 1) * 20 + random.random() * 8), 0.8, 0.25)


def bassoon_part(clock: Clock):
    clock.apply_tempo_function(lambda t: 80 + 40 * sin(t / 3), duration_units="time")
    while True:
        bassoon.play_chord([40, 44, 50], 0.8, 0.5, "staccatissimo")


flute_clock = session.fork(flute_part)
clarinet_clock = session.fork(clarinet_part)
bassoon_clock = session.fork(bassoon_part)

session.start_recording(clock=flute_clock)
# session.start_recording(clock=clarinet_clock)
# session.start_recording(clock=bassoon_clock)

session.fast_forward_in_beats(30)
session.wait(30)
session.stop_recording().to_score().show_xml()
