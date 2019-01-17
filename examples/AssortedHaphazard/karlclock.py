from scamp import Session
import random

s = Session()
piano = s.add_midi_part("piano")


def do_chords():
    while True:
        piano.play_chord([random.random()*24 + 60, random.random()*24 + 60], 1.0, 1.0)


def do_fast_notes():
    while True:
        piano.play_note(random.random()*24 + 80, 1.0, 0.1)


s.fork(do_chords)
s.fork(do_fast_notes)
s.wait_forever()
