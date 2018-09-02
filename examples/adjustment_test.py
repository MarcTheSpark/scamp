from playcorder import Playcorder

pc = Playcorder("default")

piano = pc.add_midi_part("piano", (0, 22))

while True:
    piano.play_note(65, 1, 0.25)
    piano.play_note(67, 1, 0.25, "staccato")
    piano.play_note(68, 1, 0.25, "staccato")
    piano.play_note(70, 1, 0.25, "staccato")
    piano.play_note(72, 1, 0.25, "staccato")
    piano.play_note(70, 1, 0.25, "staccato")
    piano.play_note(68, 1, 0.25, "staccato")
    piano.play_note(67, 1, 0.25, "staccato")