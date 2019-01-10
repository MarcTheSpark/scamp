from scamp import Session
import random
from pynput.keyboard import Listener

rate = 1


def on_press(key):
    try:
        global rate
        rate = 1 + int(str(key).replace("\'", ""))
        print("New rate is ", rate)
    except ValueError:
        # ignore key presses that don't correspond to number keys
        pass


# Collect events until released
Listener(on_press=on_press).start()


s = Session("default")


piano = s.add_midi_part("piano", (0, 0))


def do_chords(clock):
    while True:
        if rate != clock.rate:
            clock.rate = rate
        piano.play_chord([random.random()*24 + 60, random.random()*24 + 60], 1.0, 1.0)


def do_fast_notes(clock):
    while True:
        if rate != clock.rate:
            clock.rate = rate
        piano.play_note(random.random()*24 + 80, 1.0, 0.5)


s.fork(do_chords)
s.fork(do_fast_notes)
s.wait_forever()
