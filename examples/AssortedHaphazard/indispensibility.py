from scamp import *
from scamp_extensions.composers.barlicity import *
from pynput.mouse import Listener
import random


threshold = 0
syncopation_chance = 0


def on_move(x, y):
    global threshold, syncopation_chance
    threshold = y / 1800
    syncopation_chance = x / 2079


# Collect events until released
Listener(on_move=on_move).start()


s = Session()
drum = s.new_part("taiko", (0, 116), num_channels=150)
violin = s.new_part("violin")

indispensibilities = get_indispensability_array(((2, 3), 2, 3, (2, 3), (2, 3, 2), (3, 2, 3, 3)), True)  # (5, 7), (7, 11)

handle = None
pitch = None

while True:
    for indispensibility in indispensibilities:
        if indispensibility > 0.9:
            if handle is None:
                pitch = 65 + (1 - threshold) * 25
                handle = violin.start_note(pitch, 0.8)
            elif random.random() < 0.6:
                handle.end()
                handle = None
        elif handle is not None:
            handle.change_pitch(pitch + (1 - indispensibility) * random.uniform(-syncopation_chance * 15, syncopation_chance * 15), 0.15)

        if random.random() < syncopation_chance:
            indispensibility = 1 - indispensibility
        if indispensibility > threshold:
            drum.play_note(40 + int(80 * (1 - indispensibility)),
                           0.5 + 0.5 * (indispensibility - threshold) / (1 - threshold), 0.1)
        else:
            wait(0.1)
