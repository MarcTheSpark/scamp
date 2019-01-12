from scamp import *
import random

session = Session()

piano = session.add_midi_part("violin", (0, 40))

random.seed(1)

session.start_recording()

piano.play_note([60, 70, 50, 65, 55, 62, 58, 60], 1.0, 4.0)
piano.play_chord([[60, 70, 50, 65, 55, 62, 58, 60], [67, 77, 57, 72, 62, 69, 65, 67]], 1.0, 4.0)

performance = session.stop_recording()
engraving_settings.glissandi.inner_grace_relevance_threshold = 0
engraving_settings.glissandi.control_point_policy = "grace"
performance.to_score().show()
