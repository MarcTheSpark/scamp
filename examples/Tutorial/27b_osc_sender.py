"""
SCAMP Example: OSC Sender

This doesn't really use SCAMP; it is merely a python script that sends out a few choice osc messages of the sort that
27a_osc_listener.py is designed to respond to.
"""

from pythonosc import udp_client
import time


client = udp_client.SimpleUDPClient("127.0.0.1", 5995)

# play a chromatic scale on the piano
for x in range(65, 85):
    client.send_message("/play_note/piano", [x, 0.5, 0.1])
    time.sleep(0.1)

# play a horrifying bagpipe cluster
client.send_message("/play_bagpipe_cluster", [])
time.sleep(0.5)

# play a chromatic scale on the flute
for x in range(65, 85):
    client.send_message("/play_note/flute", [x, 0.5, 0.1])
    time.sleep(0.1)

# play another horrifying bagpipe cluster
client.send_message("/play_bagpipe_cluster", [])
time.sleep(0.5)

# play a chromatic scale alternating between flute and piano
for x in range(65, 85):
    client.send_message("/play_note/" + ("flute", "piano")[x % 2], [x, 0.5, 0.1])
    time.sleep(0.1)
