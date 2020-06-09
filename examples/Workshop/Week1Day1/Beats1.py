from scamp import *


s = Session(tempo=100, default_soundfont="beats")

s.print_default_soundfont_presets()

bass = s.new_part("bass shot")
snare = s.new_part("snare")


while True:  # Do this forever!
    bass.play_note(60, 1.0, 1)
    snare.play_note(60, 0.5, 1)
    wait(0.5)
    bass.play_note(60, 0.7, 0.5)
    snare.play_note(60, 0.5, 1)

