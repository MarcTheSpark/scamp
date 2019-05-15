from scamp import *

session = Session()
piano = session.new_part("piano")

session.start_recording()

for _ in range(2):
    piano.play_note(65, 0.5, 1.25, "accent")
    piano.play_note(67, 0.5, 0.25, "staccato")
    piano.play_note(68, 0.5, 1.25, "staccato")
    piano.play_note(70, 0.5, 0.25, "staccato")
    piano.play_note(72, 0.5, 0.25, "staccatissimo, marcato")
    piano.play_note(70, 0.5, 0.25, "staccato")
    piano.play_note(68, 0.5, 0.25, "staccato")
    piano.play_note(67, 0.5, 0.25, "staccato")

piano.play_chord([65, 77], 0.5, 2, "tenuto")

session.stop_recording().to_score().show()
