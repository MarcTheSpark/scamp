from pymusicxml import *
from random import choice, choices

score = Score(title="Algorithmically Generated MusicXML", composer="HTMLvis")
part = Part("Piano")
score.append(part)

pitch_bank = ["f#4", "bb4", "d5", "e5", "ab5", "c6", "f6"]

measures = []

for i in range(20):
    m = Measure(time_signature=(3, 4) if i == 0 else None)
    for beat_num in range(3):
        if (i + beat_num) % 3 == 0:
            # one quarter note triad
            m.append(Chord(choices(pitch_bank, k=3), 1.0))
        elif (i + beat_num) % 3 == 1:
            # two eighth note dyads
            m.append(BeamedGroup([Chord(choices(pitch_bank, k=2), 0.5) for _ in range(2)]))
        else:
            # four 16th note notes
            m.append(BeamedGroup([Note(choice(pitch_bank), 0.25) for _ in range(4)]))
    measures.append(m)
    
part.extend(measures)

score.export_to_file("AlgorithmicExample.xml")
