from scamp import *
from scamp_extensions.pitch import Scale

s = Session()

piano_treb = s.new_part("piano", clef_preference="treble", default_spelling_policy="E major")
piano_bass = s.new_part("piano", clef_preference="bass", default_spelling_policy="E major")

scl = Scale.major(64)

bass_line = [-7, -6, -5, -9, -10, -12, -13, -10, -14]

upper_parts = [-3, 0, 2]

last_bass_degree = None

def check_chord_tone(interval_with_bass):
    return interval_with_bass % 7 in (0, 2, 4)

def move_upper_parts(old_bass_note, new_bass_note):
    bass_motion = new_bass_note - old_bass_note
    bass_motion_mod = bass_motion % 7
    print(bass_motion, bass_motion_mod)
    if bass_motion_mod == 0:
        return
    elif bass_motion_mod in [1, 6]:
        # stepwise motion
        # move to nearest consonance in opposite motion to bass
        direction_to_move = -1 if bass_motion > 0 else 1
    elif bass_motion_mod in [2, 4]:
        direction_to_move = -1
    else:
        direction_to_move = 1
        
    for i, p in enumerate(upper_parts):
        while not check_chord_tone(p - new_bass_note):
            p += direction_to_move
        upper_parts[i] = p

s.start_transcribing()
for bass_degree in bass_line:
    if last_bass_degree is not None:
        move_upper_parts(last_bass_degree, bass_degree)
    last_bass_degree = bass_degree
    piano_bass.play_note(scl.degree_to_pitch(bass_degree), 1, 1, blocking=False)
    piano_treb.play_chord(scl.degree_to_pitch(upper_parts), 1, 1)
    
s.stop_transcribing().to_score().show()