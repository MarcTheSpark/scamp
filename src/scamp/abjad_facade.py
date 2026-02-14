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
