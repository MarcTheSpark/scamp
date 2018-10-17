# TODO:
#  - implement internal gracenote option for abjad as a mode
#  - in other mode, have it just do an aftergrace if the next note doesn't start at the pitch
#  - quantization for pre-splitters


# import abjad
#
# voice = abjad.Voice("c'4 <d' f'>4 <e' g'>4 f'4")
#
# overrides = """\override Glissando.minimum-length = #3
# \override Glissando.springs-and-rods = #ly:spanner::set-spacing-rods
# \override Glissando.thickness = #2"""
#
# abjad.attach(abjad.LilyPondLiteral(overrides), voice[0])
#
# notes = [abjad.Chord("<c' e'>16"), abjad.Chord("<f' a'>16")]
# after_grace_container = abjad.AfterGraceContainer(notes)
# abjad.attach(after_grace_container, voice[1])
# abjad.attach(abjad.LilyPondLiteral(r"\afterGrace"), voice[1])
#
# abjad.glissando(voice[1:3])
#
# print(voice.__format__())
# abjad.show(voice)
#
# exit()
from playcorder.score import *
from playcorder.performance import Performance
from playcorder.settings import engraving_settings

engraving_settings.glissandi.control_point_policy = "grace"
import abjad
abjad.show(Score.from_quantized_performance(Performance.load_from_json("quantized_glisses.json")).to_abjad())
