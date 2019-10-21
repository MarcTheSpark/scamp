from scamp import *
import random
import math

from scamp.settings import playback_settings

playback_settings.make_persistent()

session = Session()

shaku = session.new_part("shakuhachi")
oboe = session.new_part("oboe")

session.save_to_json(resolve_relative_path("SavedFiles/shakEnsemble.json"))


def oboe_part(clock):
    while True:
        oboe.play_note(75 + random.random() * 7 + 15 * math.sin(clock.beat() / 10), 0.4, 0.25)


def shaku_part(clock):
    assert isinstance(clock, Clock)
    pentatonic = [0, 2, 4, 7, 9]
    while True:
        if random.random() < 0.5:
            shaku.play_note(66 + random.choice(pentatonic) + 12*random.randint(0, 2),
                            Envelope.from_levels_and_durations([1.0, 0.2, 1.0, 1.0], [0.15, 0.85, 0.15], [0, 2, 0]),
                            2.5, blocking=True)
            clock.wait(0.5 + random.choice([0, 0.5]))
        else:
            shaku.play_note(66 + random.choice(pentatonic) + 12*random.randint(0, 2), 1.0, 0.2*(1+random.random()*0.3))
            clock.wait(random.choice([1, 2, 3]))


session.fork(oboe_part)
session.fork(shaku_part)

session.set_tempo_target(300, 30, duration_units="time")

session.wait(15)
session.start_transcribing()
print("Starting transcription...")
session.wait(15)
performance = session.stop_transcribing()
print("Finished. Saving transcription.")

performance.save_to_json(resolve_relative_path("SavedFiles/perfShakoboe.json"))

session.wait_forever()
