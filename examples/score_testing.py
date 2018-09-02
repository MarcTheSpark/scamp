import abjad
voice = abjad.Voice("c'4 d'4 e'4 f'4")
note = abjad.Note("cs'16")
grace_container = abjad.GraceContainer([note])
abjad.attach(grace_container, voice[1])
abjad.attach(abjad.Slur(), abjad.Selection([note, voice[1]]))
note = abjad.Note("ds'16")
after_grace_container = abjad.AfterGraceContainer([note])
abjad.attach(after_grace_container, voice[1])
abjad.show(voice)

exit()
from playcorder.score import *
from playcorder.performance import Performance

print(Performance.load_from_json("quantized_glisses.json"))

import abjad
abjad.show(Score.from_quantized_performance(Performance.load_from_json("quantized_glisses.json")).to_abjad())
