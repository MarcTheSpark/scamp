from src.scamp import *
import random

s = Session()
s.fast_forward()

violin = s.new_part("violin")

s.start_transcribing()
while s.beat() < 50:
    violin.play_note(random.randint(80, 100), 0.5, 0.25)
    
perf = s.stop_transcribing()


def apply_octava_to_part(part, threshold=90):
    part_notes = list(perf.parts[0].get_note_iterator())
    for i in range(len(part_notes)):
        last_note = part_notes[i - 1] if i > 0 else None
        this_note = part_notes[i]
        next_note = part_notes[i + 1] if i + 1 < len(part_notes) else None
        if last_note and next_note:
            if this_note.pitch > threshold:
                if last_note.pitch <= threshold and next_note.pitch <= threshold:
                    this_note.properties.texts.append(StaffText("8va", italic=True))
                elif last_note.pitch <= threshold:
                    this_note.properties.spanners.append(StartBracket(text="8va", line_type="dashed"))
            elif this_note.pitch <= threshold and last_note.pitch > threshold:
                this_note.properties.spanners.append(StopBracket())
    for note in part_notes:
        if note.pitch > threshold:
            note.pitch -= 12
     
apply_octava_to_part(perf.parts[0])
perf.to_score().show()

