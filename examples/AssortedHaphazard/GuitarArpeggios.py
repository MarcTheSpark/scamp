from scamp import *

s = Session()

guitar = s.new_part("guitar")


def play_held_arpeggio(inst, pitches, volumes, note_length, total_length):
    t = 0
    for p, v in zip(pitches, volumes):
        inst.play_note(p, v, total_length - t, blocking=False)
        wait(note_length)
        t += note_length
    wait(total_length - t)
    

while True:
    play_held_arpeggio(guitar, [45, 52, 59, 57, 60], [0.9, 0.6, 0.8, 0.5, 0.8], 0.25, 3.0)
    play_held_arpeggio(guitar, [43, 52, 59], [0.9, 0.6, 0.8], 0.25, 2.0)
    play_held_arpeggio(guitar, [41, 50, 59, 57, 60], [0.9, 0.6, 0.8, 0.5, 0.8], 0.25, 3.0)
    play_held_arpeggio(guitar, [40, 47, 56, 62], [0.9, 0.6, 0.6, 0.8], 1/3, 2.0)
