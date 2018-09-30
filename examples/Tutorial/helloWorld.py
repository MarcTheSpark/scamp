from playcorder import *

pc = Playcorder("default")

piano = pc.add_midi_part()

pc.start_recording()

pitches = [60, 62, 64, 65, 67, 69, 71, 72]
durations = [0.5, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 2.0]

for pitch, duration in zip(pitches, durations):
    piano.play_note(pitch, 1.0, duration)

performance = pc.stop_recording()

Score.from_performance(performance).show()
