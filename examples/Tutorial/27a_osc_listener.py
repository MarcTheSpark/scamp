"""
SCAMP Example: OSC Listener

Sets up an osc listener using Session.register_osc_listener, which takes in OSC messages and plays back notes and
horrific bagpipe cluster. To run this example, first run this script, and then run 27b_osc_sender.py, which sends
messages to trigger playback. (Of course, the real value of this is that incoming OSC messages can come from anywhere
and can therefore be used to modify an ongoing SCAMP process.)
"""


from scamp import *

s = Session()
piano = s.new_part("piano")
flute = s.new_part("flute")
bagpipe = s.new_part("bagpipe")


def play_note_callback(osc_address, pitch, volume, length):
    if osc_address.split("/")[-1] == "piano":
        piano.play_note(pitch, volume, length, blocking=False)
    elif osc_address.split("/")[-1] == "flute":
        flute.play_note(pitch, volume, length, blocking=False)


def bagpipe_callback(osc_address):
    bagpipe.play_chord([70, 71, 72, 73, 74, 75, 76], 0.5, 0.2, blocking=False)


s.register_osc_listener(5995, "/play_note/*", play_note_callback)
s.register_osc_listener(5995, "/play_bagpipe_cluster", bagpipe_callback)


s.wait_forever()
