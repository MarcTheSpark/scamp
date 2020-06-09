from scamp import *

s = Session()

snare = s.new_part("snare", soundfont="beats")


def mouse_listener(x, y):
    s.tempo = 60 * 2 ** (4*x-2)
    print("Tempo is:", s.tempo)
    

s.register_mouse_listener(mouse_listener, relative_coordinates=True)

while True:
    snare.play_note(60, 1, 1)