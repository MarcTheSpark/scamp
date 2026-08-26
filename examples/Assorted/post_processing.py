"""
SCAMP Example: Performance Post-Processing

Post-processes a recorded Performance of a random walk of thirds and fifths, so that every time three consecutive
notes are a triad, they are slurred together and spelled consistently.

Tags: performance post-processing, note properties, spelling
"""

from scamp import *
import random

random.seed(38)  # makes output deterministic

s = Session()
s.tempo = 120

violin = s.new_part("violin")

s.start_transcribing()

pitch = 70
while s.beat < 40:
    dur = random.choice([0.5, 1.0])
    violin.play_note(pitch, 0.5, dur)
    # go up or down by a 5th, 4th, or major or minor 3rd
    pitch += random.choice([-7, -5, -4, -3, 3, 4, 5, 7])
    if pitch < 55:
        pitch += 12
    elif pitch > 93:
        pitch -= 12

perf = s.stop_transcribing()


# ----------------- POST PROCESSING --------------------#

triads = {
    'major': [{n, (n + 4) % 12, (n + 7) % 12} for n in range(12)],
    'minor': [{n, (n + 3) % 12, (n + 7) % 12} for n in range(12)]
}

triad_spellings = {
    'major': [SpellingPolicy.all_flats() if n in (1, 3, 8, 10) else SpellingPolicy.all_sharps() for n in range(12)],
    'minor': [SpellingPolicy.all_flats() if n in (0, 3, 5, 7, 10) else SpellingPolicy.all_sharps() for n in range(12)]
}

def get_triad(pcs):
    """Determines which (if any) major or minor triad these pitch classes belong to."""
    pcs_set = set(pcs)
    if pcs_set in triads['major']:
        return 'major', triads['major'].index(pcs_set)
    elif pcs_set in triads['minor']:
        return 'minor', triads['minor'].index(pcs_set)
    return False


last_pitch_classes = []
last_notes = []

for note in perf.parts[0].get_note_iterator():
    last_notes.append(note)
    last_pitch_classes.append(note.pitch % 12)
    # only keep the last 3 pitch classes
    if len(last_notes) > 3:
        last_notes.pop(0)
        last_pitch_classes.pop(0)

    # check for a triad and process
    if len(last_pitch_classes) == 3 and (triad := get_triad(last_pitch_classes)):
        last_notes[0].properties.spanners.append(StartSlur())
        last_notes[-1].properties.spanners.append(StopSlur())

        major_minor, root = triad
        for note in last_notes:
            note.properties.spelling_policies = [triad_spellings[major_minor][root]]

        # clear the notes list so that we start fresh with the next note
        last_notes.clear()
        last_pitch_classes.clear()

perf.to_score().show()
