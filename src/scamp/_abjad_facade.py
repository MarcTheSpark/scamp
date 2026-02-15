"""
Facade module to isolate abjad API dependencies.

When abjad updates their API, only this module needs to be updated,
instead of scattered changes throughout score.py and other files.

This module uses the existing lazy loading from _dependencies.py - abjad
is only imported when first needed.
"""

#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  This file is part of SCAMP (Suite for Computer-Assisted Music in Python)                      #
#  Copyright © 2020 Marc Evanstein <marc@marcevanstein.com>.                                     #
#                                                                                                #
#  This program is free software: you can redistribute it and/or modify it under the terms of    #
#  the GNU General Public License as published by the Free Software Foundation, either version   #
#  3 of the License, or (at your option) any later version.                                      #
#                                                                                                #
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;     #
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     #
#  See the GNU General Public License for more details.                                          #
#                                                                                                #
#  You should have received a copy of the GNU General Public License along with this program.    #
#  If not, see <http://www.gnu.org/licenses/>.                                                   #
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #

from __future__ import annotations
from typing import Optional, Any, Union, TYPE_CHECKING
from ._dependencies import get_abjad

if TYPE_CHECKING:
    # Import abjad only for type checking, not at runtime
    # This allows PyCharm/mypy to understand the types while maintaining lazy loading
    import abjad

# ============================================================================
# OBJECT CREATION - constructors are the most likely to change
# ============================================================================


def create_note(pitch_name: str, duration: Optional[Union[float, int, abjad.Duration]] = None) -> abjad.Note:
    """
    Create an abjad Note with optional duration.

    :param pitch_name: Pitch name string (e.g., "c'", "d''")
    :param duration: Duration as float, int, Fraction, or abjad.Duration (will be converted if needed)
    """
    abjad = get_abjad()
    note = abjad.Note(pitch_name)
    if duration is not None:
        if not isinstance(duration, abjad.Duration):
            duration = make_abjad_duration(duration)
        note.set_written_duration(duration)
    return note


def create_chord(noteheads: Optional[list[abjad.NoteHead]] = None,
                 duration: Optional[Union[float, int, abjad.Duration]] = None) -> abjad.Chord:
    """
    Create an abjad Chord with optional noteheads and duration.

    :param noteheads: Optional list of NoteHead objects
    :param duration: Duration as float, int, Fraction, or abjad.Duration (will be converted if needed)
    """
    abjad = get_abjad()
    chord = abjad.Chord()
    if noteheads is not None:
        chord.set_note_heads(noteheads)
    if duration is not None:
        if not isinstance(duration, abjad.Duration):
            duration = make_abjad_duration(duration)
        chord.set_written_duration(duration)
    return chord


def create_rest(duration: Optional[Union[float, int, abjad.Duration]] = None) -> abjad.Rest:
    """
    Create an abjad Rest with optional duration.

    :param duration: Duration as float, int, Fraction, or abjad.Duration (will be converted if needed)
    """
    abjad = get_abjad()
    rest = abjad.Rest()
    if duration is not None:
        if not isinstance(duration, abjad.Duration):
            duration = make_abjad_duration(duration)
        rest.set_written_duration(duration)
    return rest


def create_skip(duration: Optional[Union[float, int, abjad.Duration]] = None) -> abjad.Skip:
    """
    Create an abjad Skip with optional duration.

    :param duration: Duration as float, int, Fraction, or abjad.Duration (will be converted if needed)
    """
    abjad = get_abjad()
    skip = abjad.Skip()
    if duration is not None:
        if not isinstance(duration, abjad.Duration):
            duration = make_abjad_duration(duration)
        skip.set_written_duration(duration)
    return skip


def create_voice(contents: list[Any], name: Optional[str] = None) -> abjad.Voice:
    """Create an abjad Voice."""
    abjad = get_abjad()
    return abjad.Voice(contents, name=name)


def create_staff(contents: list[Any], name: Optional[str] = None) -> abjad.Staff:
    """Create an abjad Staff."""
    abjad = get_abjad()
    return abjad.Staff(contents, name=name)


def create_staff_group(staves: list[abjad.Staff]) -> abjad.StaffGroup:
    """Create an abjad StaffGroup."""
    abjad = get_abjad()
    return abjad.StaffGroup(staves)


def create_score(parts: list[Union[abjad.Staff, abjad.StaffGroup]]) -> abjad.Score:
    """Create an abjad Score."""
    abjad = get_abjad()
    return abjad.Score(parts)


def create_container(contents: list[Any], simultaneous: bool = False) -> abjad.Container:
    """Create an abjad Container."""
    abjad = get_abjad()
    return abjad.Container(contents, simultaneous=simultaneous)


def create_tuplet(ratio_or_fraction, notes: list[Any]) -> abjad.Tuplet:
    """
    Create an abjad Tuplet.

    :param ratio_or_fraction: Either an abjad.Ratio or a Fraction (which will be converted to Ratio)
    :param notes: List of notes to include in the tuplet
    """
    from fractions import Fraction
    abjad = get_abjad()
    if isinstance(ratio_or_fraction, Fraction):
        ratio = abjad.Ratio(ratio_or_fraction.numerator, ratio_or_fraction.denominator)
    else:
        ratio = ratio_or_fraction
    return abjad.Tuplet(ratio, notes)


def create_duration(numerator: int, denominator: int) -> abjad.Duration:
    """Create an abjad Duration."""
    abjad = get_abjad()
    return abjad.Duration(numerator, denominator)


def create_ratio(numerator: int, denominator: int) -> abjad.Ratio:
    """Create an abjad Ratio for tuplets."""
    abjad = get_abjad()
    return abjad.Ratio(numerator, denominator)


def create_notehead(pitch: Any) -> abjad.NoteHead:
    """Create an abjad NoteHead."""
    abjad = get_abjad()
    return abjad.NoteHead(pitch)


def create_named_pitch(name: str, accidental: Optional[Any] = None, octave: Optional[int] = None) -> abjad.NamedPitch:
    """Create an abjad NamedPitch."""
    abjad = get_abjad()
    return abjad.NamedPitch(name, accidental=accidental, octave=octave)


def create_time_signature(time_signature: tuple) -> abjad.TimeSignature:
    """Create an abjad TimeSignature."""
    abjad = get_abjad()
    return abjad.TimeSignature(time_signature)


# ============================================================================
# PROPERTY ACCESS - handles Note vs Chord API differences
# ============================================================================


def get_noteheads(note_or_chord: Union[abjad.Note, abjad.Chord]) -> list[abjad.NoteHead]:
    """Get noteheads from Note or Chord (handles API difference)."""
    abjad = get_abjad()
    if isinstance(note_or_chord, abjad.Note):
        return [note_or_chord.note_head()]
    else:
        return note_or_chord.note_heads()


def get_written_pitches(note_or_chord: Union[abjad.Note, abjad.Chord]) -> tuple[abjad.NamedPitch, ...]:
    """Get pitches from Note or Chord (handles API difference)."""
    abjad = get_abjad()
    if isinstance(note_or_chord, abjad.Note):
        return note_or_chord.written_pitch(),
    else:
        return note_or_chord.written_pitches()


def set_written_duration(obj: Any, duration: abjad.Duration) -> None:
    """Set duration on any abjad object."""
    obj.set_written_duration(duration)


def get_written_duration(obj: Any) -> abjad.Duration:
    """Get duration from any abjad object."""
    return obj.written_duration()


# ============================================================================
# ATTACHMENT - centralize the most common operation
# ============================================================================


def attach(indicator: Any, target: Any, direction: Optional[Any] = None) -> None:
    """Attach an indicator to a target leaf."""
    abjad = get_abjad()
    if direction is not None:
        abjad.attach(indicator, target, direction=direction)
    else:
        abjad.attach(indicator, target)


# ============================================================================
# JOINING OPERATIONS
# ============================================================================


def glissando(notes):
    """Create glissando between notes."""
    abjad = get_abjad()
    abjad.glissando(notes)


def tie_notes(notes):
    """Tie notes together."""
    abjad = get_abjad()
    abjad.tie(notes)


def slur_notes(notes):
    """Slur notes together."""
    abjad = get_abjad()
    abjad.slur(notes)


def text_spanner(notes, *args, **kwargs):
    """Create text spanner across notes."""
    abjad = get_abjad()
    abjad.text_spanner(notes, *args, **kwargs)


# ============================================================================
# INDICATORS - most likely to change in API updates
# ============================================================================


def create_articulation(name: str):
    """Create an abjad Articulation."""
    abjad = get_abjad()
    return abjad.Articulation(name)


def create_clef(name: str):
    """Create an abjad Clef."""
    abjad = get_abjad()
    return abjad.Clef(name)


def create_dynamic(name: str):
    """Create an abjad Dynamic."""
    abjad = get_abjad()
    return abjad.Dynamic(name)


def create_markup(text: str):
    """Create an abjad Markup."""
    abjad = get_abjad()
    return abjad.Markup(text)


def create_metronome_mark(duration, tempo, **kwargs):
    """
    Create an abjad MetronomeMark.

    :param duration: Duration as float, int, Fraction, or abjad.Duration (will be converted if needed)
    :param tempo: Tempo value (usually an integer BPM)
    :param kwargs: Additional keyword arguments passed to abjad.MetronomeMark
    """
    abjad = get_abjad()
    if not isinstance(duration, abjad.Duration):
        duration = make_abjad_duration(duration)
    return abjad.MetronomeMark(duration, tempo, **kwargs)


def create_lilypond_literal(text: str, site: Optional[str] = None):
    """Create a LilyPondLiteral."""
    abjad = get_abjad()
    if site:
        return abjad.LilyPondLiteral(text, site=site)
    return abjad.LilyPondLiteral(text)


def create_lilypond_comment(text: str):
    """Create a LilyPondComment."""
    abjad = get_abjad()
    return abjad.LilyPondComment(text)


def create_fermata():
    """Create a Fermata."""
    abjad = get_abjad()
    return abjad.Fermata()


def create_stem_tremolo(count: int):
    """Create a StemTremolo."""
    abjad = get_abjad()
    return abjad.StemTremolo(count)


def create_arpeggio(direction: Optional[Any] = None):
    """Create an Arpeggio."""
    abjad = get_abjad()
    if direction is None:
        return abjad.Arpeggio()
    return abjad.Arpeggio(direction=direction)


def create_after_grace_container(notes: list[Any]):
    """Create an AfterGraceContainer."""
    abjad = get_abjad()
    return abjad.AfterGraceContainer(notes)


def create_voice_number(n: int):
    """Create a VoiceNumber."""
    abjad = get_abjad()
    return abjad.VoiceNumber(n=n)


def create_bar_line(style: str):
    """Create a BarLine."""
    abjad = get_abjad()
    return abjad.BarLine(style)


# ============================================================================
# SPANNERS - these return tuples
# ============================================================================


def create_start_text_span(**kwargs):
    """Create a StartTextSpan."""
    abjad = get_abjad()
    return abjad.StartTextSpan(**kwargs)


def create_stop_text_span():
    """Create a StopTextSpan."""
    abjad = get_abjad()
    return abjad.StopTextSpan()


def create_start_hairpin(shape: str):
    """Create a StartHairpin."""
    abjad = get_abjad()
    return abjad.StartHairpin(shape)


def create_stop_hairpin():
    """Create a StopHairpin."""
    abjad = get_abjad()
    return abjad.StopHairpin()


def create_start_slur():
    """Create a StartSlur."""
    abjad = get_abjad()
    return abjad.StartSlur()


def create_stop_slur():
    """Create a StopSlur."""
    abjad = get_abjad()
    return abjad.StopSlur()


def create_start_phrasing_slur():
    """Create a StartPhrasingSlur."""
    abjad = get_abjad()
    return abjad.StartPhrasingSlur()


def create_stop_phrasing_slur():
    """Create a StopPhrasingSlur."""
    abjad = get_abjad()
    return abjad.StopPhrasingSlur()


def create_start_trill_span():
    """Create a StartTrillSpan."""
    abjad = get_abjad()
    return abjad.StartTrillSpan()


def create_stop_trill_span():
    """Create a StopTrillSpan."""
    abjad = get_abjad()
    return abjad.StopTrillSpan()


def create_start_piano_pedal():
    """Create a StartPianoPedal."""
    abjad = get_abjad()
    return abjad.StartPianoPedal()


def create_stop_piano_pedal():
    """Create a StopPianoPedal."""
    abjad = get_abjad()
    return abjad.StopPianoPedal()


# ============================================================================
# LILYPOND FILE CREATION
# ============================================================================


def create_block(name: str):
    """Create an abjad Block (e.g., header, score, layout)."""
    abjad = get_abjad()
    return abjad.Block(name=name)


def create_lilypond_file(items: list[Any], **kwargs):
    """Create an abjad LilyPondFile."""
    abjad = get_abjad()
    return abjad.LilyPondFile(items=items, **kwargs)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def tweak(obj, *args, **kwargs):
    """Apply a tweak to an abjad object."""
    abjad = get_abjad()
    return abjad.tweak(obj, *args, **kwargs)


def bundle(obj, *args):
    """Bundle an object with tweaks."""
    abjad = get_abjad()
    return abjad.bundle(obj, *args)


def setting(obj):
    """Access settings on an abjad container."""
    abjad = get_abjad()
    return abjad.setting(obj)


def select_leaf(container, index: int):
    """Select a leaf from a container."""
    abjad = get_abjad()
    return abjad.select.leaf(container, index)


def parse_lilypond(string: str):
    """Parse a LilyPond string."""
    abjad = get_abjad()
    return abjad.parse(string)


def to_lilypond(obj):
    """Convert abjad object to LilyPond string."""
    abjad = get_abjad()
    return abjad.lilypond(obj)


def show(obj):
    """Show abjad object in notation software."""
    abjad = get_abjad()
    abjad.show(obj)


def persist_as_pdf(obj, *args, **kwargs):
    """Export abjad object as PDF."""
    abjad = get_abjad()
    abjad.persist.as_pdf(obj, *args, **kwargs)


# ============================================================================
# CONSTANTS
# ============================================================================


def direction_up():
    """Get UP direction constant."""
    abjad = get_abjad()
    return abjad.UP


def direction_down():
    """Get DOWN direction constant."""
    abjad = get_abjad()
    return abjad.DOWN


# ============================================================================
# TYPE CHECKING
# ============================================================================


def is_note(obj):
    """Check if object is an abjad Note."""
    abjad = get_abjad()
    return isinstance(obj, abjad.Note)


def is_chord(obj):
    """Check if object is an abjad Chord."""
    abjad = get_abjad()
    return isinstance(obj, abjad.Chord)


def is_staff_group(obj):
    """Check if object is an abjad StaffGroup."""
    abjad = get_abjad()
    return isinstance(obj, abjad.StaffGroup)


# ============================================================================
# HIGHER-LEVEL MUSICAL OPERATIONS
# These abstract common musical patterns, not just abjad API calls
# ============================================================================


def make_abjad_duration(value):
    """
    Converts a float or fraction to an abjad Duration object.

    :param value: the float or Fraction
    :return: the Duration
    """
    from fractions import Fraction
    frac = Fraction(value).limit_denominator()
    return create_duration(frac.numerator, frac.denominator)


def attach_time_signature(time_signature_string: str, voice) -> None:
    """
    Attach a time signature to a voice using LilyPond literal.
    This is a workaround for abjad issues with tuplets at measure start.

    :param time_signature_string: Time signature as string (e.g. "3/4")
    :param voice: The abjad voice to attach to
    """
    attach(create_lilypond_literal(r"\time {}".format(time_signature_string), site="opening"), voice)


def set_voice_number(voice, number: int) -> None:
    """
    Set the voice number for a voice in a polyphonic staff.
    Handles the case where the voice might be nested in containers.

    :param voice: The abjad voice
    :param number: The voice number (1, 2, 3, etc.)
    """
    attachment_spot = voice[0]
    while True:
        try:
            attach(create_voice_number(n=number), attachment_spot)
            break
        except Exception:
            attachment_spot = attachment_spot[0]


def make_measure(voices: list, clef: Optional[str] = None):
    """
    Create a measure container with simultaneous voices and optional clef.

    :param voices: List of abjad voices to include in the measure
    :param clef: Optional clef name to attach to first note
    :return: The abjad container representing the measure
    """
    abjad_measure = create_container(voices, simultaneous=True)

    if clef is not None:
        # attach the clef to the first note of the first voice
        attach(create_clef(clef), select_leaf(abjad_measure, 0))

    return abjad_measure


def create_empty_voice(time_signature, name: Optional[str] = None):
    """
    Create a voice with a full-measure rest.

    :param time_signature: TimeSignature object with numerator and denominator
    :param name: Optional name for the voice
    :return: An abjad Voice containing a full-measure rest
    """
    rest_text = "R1" if time_signature.numerator == time_signature.denominator else \
        "R1 * {}/{}".format(time_signature.numerator, time_signature.denominator)
    return create_voice(rest_text, name=name)


# ============================================================================
# COMPLEX MUSICAL OPERATIONS
# These handle common SCAMP patterns that involve multiple abjad operations
# ============================================================================


def create_styled_note(spelling_policy, pitch, duration, properties, is_glissando=False):
    """
    Create a note with pitches resolved from spelling policy, with noteheads styled and
    microtonal annotations attached.

    :param spelling_policy: SCAMP SpellingPolicy object
    :param pitch: Pitch value (MIDI number or pitch at time point)
    :param duration: Duration value
    :param properties: SCAMP NoteProperties object
    :param is_glissando: Whether this is part of a glissando (affects which pitch to use)
    :return: Styled abjad Note
    """
    from ._engraving_translations import get_lilypond_notehead_tweaks

    pitch_obj = pitch.start_level() if is_glissando else pitch
    pitch_name = spelling_policy.resolve_abjad_pitch(pitch_obj).name()
    note = create_note(pitch_name, duration=duration)

    # Set notehead styles
    note_head = note.note_head()
    tweak_string, comment = get_lilypond_notehead_tweaks(properties.noteheads[0])
    if tweak_string:
        tweak(note_head, tweak_string)
    if comment:
        attach(create_lilypond_comment(comment), note)

    # Attach microtonal annotations if needed
    attach_microtonal_annotation(note, pitch_obj, properties)

    return note


def create_styled_chord(spelling_policies, pitches, duration, properties, is_glissando=False):
    """
    Create a chord with pitches resolved from spelling policies, noteheads styled and
    microtonal annotations attached.

    :param spelling_policies: List of SCAMP SpellingPolicy objects (one per pitch)
    :param pitches: List of pitch values
    :param duration: Duration value
    :param properties: SCAMP NoteProperties object
    :param is_glissando: Whether this is part of a glissando (affects which pitches to use)
    :return: Styled abjad Chord
    """
    from ._engraving_translations import get_lilypond_notehead_tweaks

    chord = create_chord(duration=duration)

    # Create and set noteheads
    pitch_objs = [p.start_level() if is_glissando else p for p in pitches]
    noteheads = [
        create_notehead(spelling_policies[i].resolve_abjad_pitch(pitch_obj))
        for i, pitch_obj in enumerate(pitch_objs)
    ]
    chord.set_note_heads(noteheads)

    # Set notehead styles
    note_heads = get_noteheads(chord)
    for note_head, notehead_string in zip(note_heads, properties.noteheads):
        tweak_string, comment = get_lilypond_notehead_tweaks(notehead_string)
        if tweak_string:
            tweak(note_head, tweak_string)
        if comment:
            attach(create_lilypond_comment(comment), chord)

    # Attach microtonal annotations if needed
    attach_microtonal_annotation(chord, pitch_objs, properties)

    return chord


def attach_glissando_grace_notes(main_note, grace_note_or_chord_list, stemless=True):
    """
    Create an AfterGraceContainer with grace notes, optionally mark them as stemless,
    and attach to the main note.

    :param main_note: The main abjad note/chord to attach grace notes to
    :param grace_note_or_chord_list: List of abjad grace notes/chords
    :param stemless: Whether to add \\stemless literal to grace notes
    :return: The created AfterGraceContainer
    """
    if stemless:
        for grace_note in grace_note_or_chord_list:
            attach(create_lilypond_literal(r"\stemless"), grace_note)

    grace_container = create_after_grace_container(grace_note_or_chord_list)
    attach(grace_container, main_note)

    return grace_container


def create_tempo_voice(score_measure, displacements, metronome_mark_beat_length):
    """
    Create a voice filled with skips for attaching tempo markings, with optimized
    skip combining for cleaner output.

    :param score_measure: SCAMP Measure object
    :param displacements: List of beat positions where tempo marks occur
    :param metronome_mark_beat_length: Beat length for metronome marks
    :return: Tuple of (tempo_voice, mark_beats_to_skip_objects dict)
    """
    from fractions import Fraction

    if len(displacements) == 0:
        skip_length = 1 / Fraction(score_measure.length / 4).denominator
        skips = [create_skip(duration=0.25 * skip_length)
                 for _ in range(int(round(score_measure.length / skip_length)))]
        return create_voice(skips, name="TempoVoice"), None

    # length of the skips in quarter notes
    min_skip = 1 / Fraction(score_measure.length).denominator
    while max(x % min_skip for x in displacements) > 0.05:
        min_skip /= 2

    skips = [create_skip(duration=0.25 * min_skip)
             for _ in range(int(round(score_measure.length / min_skip)))]

    # maps the beat of any of the key points and guide marks we will run into to the skip object
    # that most nearly approximates its position
    mark_beats_to_skip_objects = {x: skips[int(x / min_skip)] for x in displacements}

    # Now combine skips when possible for cleaner output
    def combine_skips_as_possible(chunk, combination_size):
        if combination_size < 0.25 * min_skip:
            return chunk
        out = []
        skips_per_sub_chunk = int(round(combination_size / (0.25 * min_skip)))
        for sub_chunk in (chunk[i: i + skips_per_sub_chunk]
                         for i in range(0, len(chunk), skips_per_sub_chunk)):
            if not any(x in mark_beats_to_skip_objects.values() for x in sub_chunk[1:]):
                # we can combine the skips so long as none except the first are locations where tempo marks occur
                combined_skip = create_skip(duration=combination_size)
                # if a tempo mark occurs at the first skip in the chunk, we can still combine it, but we have to be
                # careful to remap the mark_beats_to_skip_objects dictionary to point to the new combined skip
                for x in mark_beats_to_skip_objects:
                    if mark_beats_to_skip_objects[x] == sub_chunk[0]:
                        mark_beats_to_skip_objects[x] = combined_skip
                out.append(combined_skip)
            else:
                out.extend(combine_skips_as_possible(sub_chunk, combination_size / 2))
        return out

    # Start by trying to chunk things into the largest un-dotted note that divides the measure
    skips = combine_skips_as_possible(skips, 1 / Fraction(score_measure.length / 4).denominator)

    tempo_voice = create_voice(skips, name="TempoVoice")

    return tempo_voice, mark_beats_to_skip_objects


def attach_articulations(properties, target, grace_container=None):
    """
    Attach articulations from SCAMP NoteProperties to an abjad note/chord,
    with intelligent handling of attack/inner/release articulations for glissandi.

    :param properties: SCAMP NoteProperties object
    :param target: Main abjad note/chord
    :param grace_container: Optional AfterGraceContainer for glissandi
    """
    if grace_container is None:
        # just a single notehead, so attach all articulations
        for articulation in properties.articulations:
            attach(create_articulation(articulation), target)
    else:
        # there's a gliss - need to handle attack/inner/release articulations
        from .note_properties import NoteProperties  # Import locally to avoid circular dependency

        attack_notehead = target if not properties.ends_tie else None
        release_notehead = grace_container[-1] if not properties.starts_tie else None
        inner_noteheads = ([] if attack_notehead is not None else [target]) + \
                          [grace for grace in grace_container[:-1]] + \
                          ([] if release_notehead is not None else [grace_container[-1]])

        # Helper functions to get attack/inner/release articulations
        def get_attack_articulations():
            return [x.split()[0] for x in properties.articulations if "attack" in x or " " not in x]

        def get_inner_articulations():
            return [x.split()[1] for x in properties.articulations if "inner" in x]

        def get_release_articulations():
            return [x.split()[-1] for x in properties.articulations if "release" in x]

        # only attach attack articulations to the main note
        if attack_notehead is not None:
            for articulation in get_attack_articulations():
                attach(create_articulation(articulation), attack_notehead)
        # attach inner articulations to all but the last notehead in the grace container
        for articulation in get_inner_articulations():
            for grace_note in inner_noteheads:
                attach(create_articulation(articulation), grace_note)
        # attach release articulations to the last notehead in the grace container
        if release_notehead is not None:
            for articulation in get_release_articulations():
                attach(create_articulation(articulation), release_notehead)


def attach_markup(text_or_markup, target, placement="above"):
    """
    Attach markup to a target with specified placement.

    :param text_or_markup: String or abjad Markup object
    :param target: Abjad note/chord to attach to
    :param placement: "above", "below", or None
    """
    if isinstance(text_or_markup, str):
        markup = create_markup(text_or_markup)
    else:
        markup = text_or_markup

    direction = direction_up() if placement == "above" else \
                direction_down() if placement == "below" else None

    attach(markup, target, direction=direction)


def create_named_staff(contents, name):
    """
    Create a staff with instrument name set.

    :param contents: List of abjad components
    :param name: Staff name (also used as instrument name)
    :return: Abjad Staff
    """
    staff = create_staff(contents, name=name)
    setting(staff).instrument_name = '#"{}"'.format(name)
    return staff


def create_score_with_top_staff(parts):
    """
    Create a score and return it along with the top staff (for tempo marking attachment).

    :param parts: List of abjad Staff or StaffGroup objects
    :return: Tuple of (score, top_staff)
    """
    score = create_score(parts)
    # tempo markings will be attached to the top staff
    # Here we sort out whether or not that staff is part of a staff group or not
    top_staff = score[0][0] if is_staff_group(score[0]) else score[0]
    return score, top_staff


def attach_microtonal_annotation(note_or_chord, pitch_or_pitches, properties):
    """
    Attach microtonal annotation markup to a note/chord if needed.

    :param note_or_chord: Abjad note or chord
    :param pitch_or_pitches: Single pitch or list of pitches (MIDI numbers)
    :param properties: SCAMP NoteProperties object
    """
    from .settings import engraving_settings

    if not engraving_settings.show_microtonal_annotations or \
            properties.ends_tie and not hasattr(pitch_or_pitches, '__iter__'):
        # if this is not the first segment of the note, and it's not part of a gliss, don't do the annotations
        return

    if hasattr(pitch_or_pitches, '__len__'):
        if any(round(p, engraving_settings.microtonal_annotation_digits) != round(p) for p in pitch_or_pitches):
            markup = create_markup(
                r'\markup { \pitch-annotation "' +
                "; ".join(str(round(p, engraving_settings.microtonal_annotation_digits))
                          for p in pitch_or_pitches) +
                '" }')
            attach(markup, note_or_chord, direction=direction_up())
    else:
        if round(pitch_or_pitches, engraving_settings.microtonal_annotation_digits) != round(pitch_or_pitches):
            markup = create_markup(
                r'\markup { \pitch-annotation "' +
                str(round(pitch_or_pitches, engraving_settings.microtonal_annotation_digits)) + '" }')
            attach(markup, note_or_chord, direction=direction_up())


def attach_notations(properties, target, grace_container=None):
    """
    Attach notations from SCAMP NoteProperties to an abjad note/chord.

    :param properties: SCAMP NoteProperties object
    :param target: Main abjad note/chord
    :param grace_container: Optional AfterGraceContainer for glissandi
    """
    from ._engraving_translations import attach_abjad_notation_to_note

    if grace_container is None:
        # just a single notehead, so attach all notations
        for notation in properties.notations:
            attach_abjad_notation_to_note(target, notation)
    else:
        # there's a gliss - need to handle attack/inner/release notations
        attack_notehead = target if not properties.ends_tie else None
        release_notehead = grace_container[-1] if not properties.starts_tie else None
        inner_noteheads = ([] if attack_notehead is not None else [target]) + \
                          [grace for grace in grace_container[:-1]] + \
                          ([] if release_notehead is not None else [grace_container[-1]])

        # Helper functions to get attack/inner/release notations
        def get_attack_notations():
            return [x.split()[0] for x in properties.notations if "attack" in x or " " not in x]

        def get_inner_notations():
            return [x.split()[1] for x in properties.notations if "inner" in x]

        def get_release_notations():
            return [x.split()[-1] for x in properties.notations if "release" in x]

        # only attach attack notations to the main note
        if attack_notehead is not None:
            for notation in get_attack_notations():
                attach_abjad_notation_to_note(attack_notehead, notation)
        # attach inner notations to all but the last notehead in the grace container
        for notation in get_inner_notations():
            for grace_note in inner_noteheads:
                attach_abjad_notation_to_note(grace_note, notation)
        # attach release notations to the last notehead in the grace container
        if release_notehead is not None:
            for notation in get_release_notations():
                attach_abjad_notation_to_note(release_notehead, notation)


def attach_spanners(properties, target, grace_container=None):
    """
    Attach spanners from SCAMP NoteProperties to an abjad note/chord.

    :param properties: SCAMP NoteProperties object
    :param target: Main abjad note/chord
    :param grace_container: Optional AfterGraceContainer for glissandi
    """
    def attach_spanner(spanner, spanner_target):
        """Helper to attach a single spanner."""
        for spanner_abjad_object in spanner.to_abjad():
            attach(
                spanner_abjad_object, spanner_target,
                direction=spanner.get_abjad_direction()
            )

    if grace_container is None:
        # just a single notehead, so attach all spanners
        for spanner in properties.spanners:
            attach_spanner(spanner, target)
    else:
        # there's a gliss - need to handle start/stop spanners
        attack_notehead = target if not properties.ends_tie else None
        release_notehead = grace_container[-1] if not properties.starts_tie else None

        # Helper functions to get start/mid/stop spanners
        def get_start_and_mid_spanners():
            return [s for s in properties.spanners if "start" in s.__class__.__name__.lower()
                    or "change" in s.__class__.__name__.lower()]

        def get_stop_spanners():
            return [s for s in properties.spanners if "stop" in s.__class__.__name__.lower()]

        if attack_notehead is not None:
            for spanner in get_start_and_mid_spanners():
                attach_spanner(spanner, attack_notehead)
        if release_notehead is not None:
            for spanner in get_stop_spanners():
                attach_spanner(spanner, release_notehead)


def attach_texts_and_dynamics(properties, target):
    """
    Attach text annotations and dynamics from SCAMP NoteProperties to an abjad note/chord.

    :param properties: SCAMP NoteProperties object
    :param target: Abjad note/chord
    """
    from .text import StaffText

    for i, text in enumerate(properties.texts):
        assert isinstance(text, StaffText)
        if len(properties.texts) > 1:
            # we want texts to appear in the order that they have been added to the note, but since 3.9,
            # abjad alphabetizes everything. So we need to set outside-staff-priority explicitly
            # 450 is the default outside-staff-priority
            text_object = bundle(text.to_abjad(), rf'\tweak outside-staff-priority #{450 + i}')
        else:
            text_object = text.to_abjad()
        attach(
            text_object, target,
            direction=direction_up() if text.placement == "above" else direction_down()
        )
    for dynamic in properties.dynamics:
        attach(create_dynamic(dynamic), target)
