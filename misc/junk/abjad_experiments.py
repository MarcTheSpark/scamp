import abjad

measure = abjad.Container()
tuplet = abjad.Tuplet((4, 5))
measure.extend(r"\times 4/5 { c'4 r16 } r4 f'2")
abjad.attach(abjad.LilyPondLiteral(r"\stemless"), measure[-1])
# print(format(measure))
# abjad.show(measure)
score = abjad.Score([measure])


file_definitions = "% Definitions to improve score readability\n" \
               "stemless = {\n" \
               "    \once \override Beam.stencil = ##f\n" \
               "    \once \override Flag.stencil = ##f\n" \
               "    \once \override Stem.stencil = ##f\n" \
               "}"

score_overrides = "% improve glissando appearance and readability" \
                 "\override Score.Glissando.minimum-length = #4\n" \
                 "\override Score.Glissando.springs-and-rods = #ly:spanner::set-spacing-rods\n" \
                 "\override Score.Glissando.thickness = #2\n" \
                 "\override Score.Glissando #'breakable = ##t"

abjad.attach(abjad.LilyPondLiteral(score_overrides), score)

lilypond_file = abjad.LilyPondFile.new(
    music=score,
    default_paper_size=('a5', 'portrait'),
    global_staff_size=16,
)

# lilypond_file.items.insert(-1, file_definitions)
abjad.attach(file_definitions, lilypond_file)
print(format(lilypond_file))
abjad.show(lilypond_file)
