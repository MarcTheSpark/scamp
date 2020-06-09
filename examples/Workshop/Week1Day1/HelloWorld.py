from scamp import *

s = Session()

piano = s.new_part("piano")

piano.play_note(60, 0.5, 2.0)
