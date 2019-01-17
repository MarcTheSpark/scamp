from scamp import *

session = Session()

engraving_settings.tempo.include_guide_marks = True

violin = session.add_midi_part("violin")

session.master_clock.set_tempo_target(100, 5)
session.master_clock.set_tempo_target(135, 9, truncate=False)
session.master_clock.set_tempo_target(135, 14, truncate=False)
session.master_clock.set_tempo_target(40, 18, truncate=False)
session.master_clock.set_tempo_target(100, 18, truncate=False)
session.master_clock.set_tempo_target(89, 27, truncate=False)

session.start_recording()
session.fast_forward_in_beats(30)

while session.beats() < 30:
    violin.play_note(70 + (session.beats() * 3) % 7, 1.0, 0.25)

performance = session.stop_recording()

performance.to_score("5/8").show_xml()
