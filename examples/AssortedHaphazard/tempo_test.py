from scamp import *

session = Session()
session.fast_forward_in_time(100)

engraving_settings.tempo.include_guide_marks = False

violin = session.new_part("violin")

session.set_tempo_target(100, 5)
session.set_tempo_target(135, 26/3, truncate=False)
session.set_tempo_target(135, 14, truncate=False)
session.set_tempo_target(40, 18, truncate=False)
session.set_tempo_target(100, 18, truncate=False)
session.set_tempo_target(89, 27, truncate=False)

session.start_transcribing()

while session.beat() < 30:
    violin.play_note(70 + (session.beat() * 3) % 7, 1.0, 0.25)

performance = session.stop_transcribing()

# performance.to_score(time_signature="5/8").print_lilypond(True)
bob = [1.5]
import random
while bob[-1] < 50:
    bob.append(bob[-1] + random.randint(1, 30) * 0.25)

print(bob)
performance.to_score(bar_line_locations=bob).print_lilypond(True)
performance.to_score(bar_line_locations=bob).show()
