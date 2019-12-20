from scamp import *

s = Session()
piano = s.new_part("piano")


def child(clock: Clock):
    clock.apply_tempo_function(lambda b: 90 + 60 * math.sin(b / 5))
    global grand_child_clock
    grand_child_clock = clock.fork(grand_child)
    while True:
        wait(1)


def grand_child(clock: Clock):
    clock.rate = 2
    while True:
        piano.play_note(103, 1, 1)
        piano.play_note(103, 1, 1)
        piano.play_note(103, 1, 1)
        piano.play_note(103, 1, 1)
        clock.rate = 1 / clock.rate


def play_wiggle(p, transposition=0):
    for _ in range(2):
        piano.play_note(p + transposition, 0.5, 0.25)
        piano.play_note(p+1 + transposition, 0.5, 0.25)
        piano.play_note(p + transposition, 0.5, 0.25)
        piano.play_note(p-1 + transposition, 0.5, 0.25)


def key_down(name, number):
    if 20 < number < 110:
        grand_child_clock.fork(play_wiggle, args=(number, ))


grand_child_clock = None
child_clock = s.fork(child)
s.register_keyboard_listener(on_press=key_down, suppress=True)

while True:
    piano.play_note(108, 1.0, 1)
    s.wait(1)
