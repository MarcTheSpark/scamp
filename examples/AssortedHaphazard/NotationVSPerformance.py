from scamp import *

s = Session()

Steel_drums=s.new_part("Steel Drum")
Steel_drums_notation=s.new_silent_part("Steel Drum (clean notation)")

straight_performance = s.start_transcribing(Steel_drums_notation)
wonky_performance = s.start_transcribing(Steel_drums)


def _play_straight_beat(pitches):
    for pitch, dur in zip(pitches, [0.25] * 4):
        Steel_drums_notation.play_note(pitch, 0.5, dur)
        
def play_one_beat_drums(pitches, subdivision_durs=(0.26, 0.23, 0.24, 0.27)):
    fork(_play_straight_beat, args=[pitches])
    for pitch, dur in zip(pitches, subdivision_durs):
        Steel_drums.play_note(pitch, 0.5, dur)
   

for _ in range(4):  # do it 4 times
    play_one_beat_drums([60, 61, 62, 63])


s.stop_transcribing(straight_performance)
s.stop_transcribing(wonky_performance)
wonky_performance.export_to_midi_file("wonky.mid")
# If you check out the score, it takes into acount the intern elasticity produced by apply_rate_function
partition = straight_performance.to_score(title="Elasticity", time_signature="4/4", composer="decomposer & Co")
partition.show()