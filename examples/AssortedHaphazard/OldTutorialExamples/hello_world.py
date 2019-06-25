from scamp import *

session = Session()

piano = session.new_part("piano")

session.start_recording()

pitches = [60, 62, 64, 65, 67, 69, 71, 72]
durations = [0.5, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 2.0]

for pitch, duration in zip(pitches, durations):
    piano.play_note(pitch, 1.0, duration)

performance = session.stop_recording()

performance.to_score().show()
