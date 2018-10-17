from playcorder import Playcorder, Clock, Envelope
import random
import math

pc = Playcorder("default")

shaku = pc.add_midi_part("shakuhachi", (0, 77))
oboe = pc.add_midi_part("oboe", (0, 68))

pc.ensemble.save_to_json("shakEnsemble.json")


def oboe_part(clock):
    while True:
        oboe.play_note(75 + random.random()*7 + 15 * math.sin(clock.beats()/10), 0.4, 0.25)


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


pc.fork(oboe_part)
pc.fork(shaku_part)

pc.master_clock.set_tempo_target(300, 30, duration_units="time")
# pc.master_clock.timing_policy = "relative"

pc.wait(15)
pc.start_recording()
print("Starting recording...")
pc.wait(15)
performance = pc.stop_recording()
print("Finished. Saving recording.")

performance.save_to_json("perfShakoboe.json")
# pc.master_clock.wait(2)

pc.wait_forever()

# 598