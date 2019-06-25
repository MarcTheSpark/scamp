from scamp import *

s = Session()

piano = s.new_part("piano")
s.start_recording()

# spell the note with a sharp
piano.play_note(63, 1.0, 1.0, "#")

# play some notes in F minor
pitches = [65, 63, 61, 60]
durations = [1/3] * 3 + [1]
for pitch, dur in zip(pitches, durations):
	piano.play_note(pitch, 1.0, dur,
					         "key: F minor")

s.stop_recording().to_score().show()
exit()
piano = s.new_part("piano").add_streaming_midi_playback(0)
synth = s.new_osc_part("synth", ip_address="127.0.0.1",
                       port=57120)
# s.start_recording()
# piano.play_note(e, 1.0, 4)
# s.stop_recording().to_score().show_xml()
#
# # pitch list interpreted as evenly spaced glissando
# piano.play_note([60, 70, 55], 1.0, 4)
# # a nested list will be interpreted as
# # [[-values-], [-durations-], [-curve shapes-]]
# piano.play_note([[60, 70, 55], [2, 1], [-2, 0]], 1.0, 4)
s.start_recording()

engraving_settings.\
    show_microtonal_annotations = True
piano.play_note(62.3, 1.0, 1)
piano.play_note(65.2, 1.0, 1)
piano.play_note(71.5, 1.0, 1)
wait(5)
s.stop_recording().to_score().show_xml()


exit()

from clockblocks import *
from threading import Event

c = Clock("MASTER")


def para():
    wait(1.5)
    print("poo")
    print(c._ready_and_waiting)
    c._wait_event.set()
    # interruptable.set()


c.fork_unsynchronized(para)
print("hey")
c.wait(3)
print("ho")


exit()











from scamp import *
from clockblocks.debug import log_multi
import threading
import traceback

old_sleep = time.sleep

def sub_sleep(secs):
    if current_clock() is not None:
        log_multi("sleep call", "t", secs)
    old_sleep(secs)

time.sleep = sub_sleep

# inst = ScampInstrument().add_streaming_midi_playback(1, num_channels=8, max_pitch_bend=48)
# h = inst.start_note(60, 1.0)
# time.sleep(1)
# h.change_pitch(62)
# time.sleep(1)
# h.end()
# exit()
import random

s = Session()

s.print_available_ports_and_devices()
# piano = s.new_part("piano")
piano = s.new_midi_part("piano", midi_output_device=1, num_channels=8, max_pitch_bend=20)


def midi_callback(midi_message):
    code, pitch, volume = midi_message
    if volume > 0 and code == 144:
        volume /= 127
        x = 4 + 8 * (random.random())
        if random.random() > 0.5:
            x *= -1
        length = ((127 - pitch) / 127 + random.random() * 0.3) * 8

        pitch_env = Envelope.from_list([[pitch, pitch + x, pitch - x, pitch + x, pitch - x], [1, 1, 1, 5]])
        piano.play_note(pitch_env, [[0, volume, volume], [0.1, 0.99]], length, blocking=False, clock=s)
        # piano.play_note(pitch_env + 6, [[0, volume, volume], [0.01, 0.99]], length, blocking=False, clock=s)


s.register_midi_callback(1, midi_callback)
while True:
    print("P")
    piano.play_note(60, 0.3, 1)
# pitch = 60
# x = 12
# volume = 0.7
# length = ((127 - pitch) / 127 + random.random() * 0.3) * 8
# # piano.set_max_pitch_bend(48)
#
# piano.play_note([[pitch, pitch + x, pitch - x, pitch + x, pitch - x, pitch - x], [1, 1, 1, 1, 5]], [[0, volume, volume], [0.01, 0.99]], length, blocking=False)

s.wait_forever()
