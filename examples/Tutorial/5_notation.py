"""
SCAMP Example: Generating Notation

Plays a simple C Major arpeggio, and generates notation for it.
"""

from scamp import *

s = Session()
violin = s.new_part("Violin")

# begin recording (defaults to transcribing all instruments within the session)
s.start_transcribing()
for pitch in [60, 64, 67, 72]:
    violin.play_note(pitch, 1, 0.5)
    # stop the recording and save the recorded
    # note events as a performance

# a Performance is essentially a note event list representing exactly
# when and how notes were played back, in continuous time
performance = s.stop_transcribing()
# quantize and convert the performance to a Score object and
# open it as a PDF (by default this is done via abjad)
performance.to_score().show()

exit()  # the other options below will not be run unless you comment out this line

# -------------------------------------------- MusicXML Notation ----------------------------------------------

# If instead you want the notation created in MusicXML format
# and opened up in MuseScore, Sibelius, or Finale, run this command:
performance.to_score().show_xml()
# Note that by default, SCAMP tries to find an appropriate application to open MusicXML files when it is first run
# If you want to change which application SCAMP uses (e.g. to Sibelius), run the following command
engraving_settings.set_show_music_xml_application("Sibelius")
# ... and then run this command so that SCAMP remembers the setting
engraving_settings.make_persistent()

# ----------------------------------------- Export Rather Than Show -------------------------------------------

# if, instead of opening up the notation, you merely want to save it to a file, you can run one of the following:
performance.to_score().export_lilypond("NotationExample.ly")
performance.to_score().export_music_xml("NotationExample.xml")

# -------------------------------------- Printing MusicXML / LilyPond -----------------------------------------

# if you just want to print the LilyPond or MusicXML markup, you can instead run:
performance.to_score().print_lilypond()
performance.to_score().print_music_xml()
