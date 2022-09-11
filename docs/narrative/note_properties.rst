.. _The Note Properties Argument:

The Note Properties Argument
============================

When you play a note in SCAMP, in addition to providing a pitch, volume and duration, you can provide an optional
fourth argument consisting of various additional note properties:

- *articulations*, such as staccato/legato
- *notations*, such as ornaments, fermatas, tremolo, etc.
- *noteheads*, such as diamond, x, etc.
- *spanners*, such as text brackets, hairpins, pedal markings, etc.
- *dynamics*, such as f, p, fp
- *texts*, such as expressive and technique markings
- *playback_adjustments*, which allow the playback of a note to differ from
  its notation. (For example, you might obtain a legato effect by making the note
  last longer than notated so that it overlaps with the next note.)
- *spelling_policy*, which determines how pitches are spelled
- *voice*, which determines which voice a note gets placed in when generating
  notation.
- *extra_playback_parameters*, which can be used to control MIDI CC messages,
  as well as arbitrary synthesis parameters when a method of playback supports
  such parameters.

What you pass to the properties argument can take a number of different forms, all of which
are ultimately converted into a :class:`~scamp.note_properties.NoteProperties` object:

- A string of comma-separated property descriptions
- A single subtype of :class:`~scamp.utilities.NoteProperty`, such as a
  :class:`~scamp.spelling.SpellingPolicy`, :class:`~scamp.text.StaffText`,
  :class:`~scamp.playback_adjustments.NotePlaybackAdjustment`, or any of
  the :class:`~scamp.spanners.Spanner` subtypes.
- A dictionary with keys "articulations", "noteheads", "notations", etc.
- a :class:`~scamp.note_properties.NoteProperties` object itself
- A list of any of the the above, which get merged into a single :class:`~scamp.note_properties.NoteProperties`

In practice, the easiest way to use the properties argument is by passing a string,
which acts as a kind of shorthand. For example, if you simply pass the string, "tenuto",
SCAMP will interpret this as an articulation. Thus, the following are equivalent:

.. code-block:: python3

    inst.play_note(60, 1, 1, "tenuto")
    inst.play_note(60, 1, 1, {"articulations": ["tenuto"]})

In practice, the ability to define note properties in various different ways --- and to combine these representations
on the fly in a list --- leads to considerable flexibility. Consider the following example, in which we create a
`NoteProperties` object called `harmonic` that combines a harmonic notehead with a playback transposition up an octave.
We then pass this object as part of a list of other note properties to the notes being played:

.. code-block:: python3

    harmonic = NoteProperties("notehead: harmonic", "pitch + 12")
    for i, pitch in enumerate(range(70, 79)):
        if i % 3 == 0:
            inst.play_note(pitch, 1, 1/3, [harmonic, "staccato", StartSlur()])
        elif i % 3 == 2:
            inst.play_note(pitch, 1, 1 / 3, [harmonic, "staccato", StopSlur()])
        else:
            inst.play_note(pitch, 1, 1/3, [harmonic, "staccato"])

    inst.play_chord([67, 79], 1.0, 1, "accent, fermata")

The result is that the notes with the harmonic sound an octave higher, and the notation looks like this:

.. image:: PropertiesExample.png
  :width: 400
  :alt: An example of note properties in action.
  :align: center


Below are examples for each kind of note property, along with an comprehensive catalog of all the possible playback
modifications and notations that are possible in SCAMP.

:ref:`Articulations` |
:ref:`Notations` |
:ref:`Noteheads` |
:ref:`Spanners` |
:ref:`Dynamics` |
:ref:`Staff Text` |
:ref:`Playback Adjustments` |
:ref:`Spelling Policy` |
:ref:`Voices` |
:ref:`Extra Playback Parameters`

.. _Articulations:

Articulations
-------------

To play a note with a staccato articulation, you can do any of the following:

.. code-block:: python3

    inst.play_note(60, 1, 1, "staccato")
    inst.play_note(60, 1, 1, "articulation: staccato")
    inst.play_note(60, 1, 1, {"articulations": ["staccato"]})

Available articulations are: "staccato", "staccatissimo", "marcato", "tenuto",
and "accent".

.. _Notations:

Notations
---------

To play a note with a fermata notation, you can do any of the following:

.. code-block:: python3

    inst.play_note(60, 1, 1, "fermata")
    inst.play_note(60, 1, 1, "notation: fermata")
    inst.play_note(60, 1, 1, {"notations": ["fermata"]})

Available notations are: "tremolo", "tremolo1", "tremolo2", "tremolo3",
"tremolo4", "tremolo5", "tremolo6", "tremolo7", "tremolo8", "down-bow",
"up-bow", "open-string", "harmonic", "stopped", "snap-pizzicato", "arpeggiate",
"arpeggiate up", "arpeggiate down", "non-arpeggiate", "fermata", "turn",
"mordent", "inverted mordent", "trill mark".

.. _Noteheads:

Noteheads
---------

To play a note with an "x" as its notehead, you can do any of the following:

.. code-block:: python3

    inst.play_note(60, 1, 1, "x")
    inst.play_note(60, 1, 1, "notehead: x")
    inst.play_note(60, 1, 1, {"noteheads": ["x"]})

If you want to play a chord with different noteheads for different pitches
(for example when playing an artificial harmonic), you can do any of the
following:

.. code-block:: python3

    inst.play_chord([60, 65], 1, 1, "regular/x")
    inst.play_chord([60, 65], 1, 1, "notehead: regular/x")
    inst.play_chord([60, 65], 1, 1, {"noteheads": ["regular", "x"]})

Available noteheads (based on the MusicXML standard) are:
"normal", "diamond", "harmonic", "harmonic-black", "harmonic-mixed", "triangle",
"slash", "cross", "x", "circle-x", "xcircle", "inverted triangle", "square",
"arrow down", "arrow up", "circled", "slashed", "back slashed", "cluster",
"circle dot", "left triangle", "rectangle", "do", "re", "mi", "fa", "fa up",
"so", "la", "ti", "none". Any of these can be preceded by "open" or "filled",
e.g. "open triangle" or "filled diamond".

.. _Spanners:

Spanners
--------

Spanners are notations that span multiple notes, so to create a spanner, you will need
a start spanner attached to one note and a stop spanner attached to another note. For
example, in order to play a slur over several notes you could do:

.. code-block:: python3

    inst.play_note(60, 1, 0.5, "start slur")
    inst.play_note(62, 1, 0.5)
    inst.play_note(64, 1, 0.5, "stop slur")

This uses the string shorthand, but you can also start a slur in any of the following
ways:

.. code-block:: python3

    inst.play_note(60, 1, 0.5, StartSlur())
    inst.play_note(60, 1, 0.5, "spanner: start slur")
    inst.play_note(60, 1, 0.5, {"spanners": "start slur"})
    inst.play_note(60, 1, 0.5, {"spanners": StartSlur()})

While slurs are pretty simple in nature, for other spanners you may need to specify text, positioning above
or below the staff, and other details. These details can be provided as arguments to the relevant spanner
class, or as additional words or phrases in the string shorthand. For example, to start a dashed text bracket
specifying sul ponticello technique, you could do either of the following:

.. code-block:: python3

    inst.play_note(60, 1, 0.5, StartBracket(text="sul pont.", line_type="dashed"))
    inst.play_note(60, 1, 0.5, "start bracket dashed 'sul pont.'")

The following table lays out the different possible spanner types, and examples of their string shorthand.

.. list-table:: Spanner Types
    :widths: 25 50 70
    :header-rows: 1

    * - Spanner Type
      - Associated Classes
      - String Shorthand Example
    * - Slur
      - :class:`~scamp.spanners.StartSlur`, :class:`~scamp.spanners.StopSlur`
      - "start slur", "stop slur"
    * - Phrasing slur
      - :class:`~scamp.spanners.StartPhrasingSlur`, :class:`~scamp.spanners.StopPhrasingSlur`
      - "start phrasing slur", "stop phrasing slur"
    * - Hairpin
      - :class:`~scamp.spanners.StartHairpin`, :class:`~scamp.spanners.StopHairpin`
      - "start hairpin >", "start hairpin o< above"
    * - Bracket
      - :class:`~scamp.spanners.StartBracket`, :class:`~scamp.spanners.StopBracket`
      - "start bracket dashed 'sul pont.'", "stop bracket", "start bracket solid below"
    * - Dashes
      - :class:`~scamp.spanners.StartDashes`, :class:`~scamp.spanners.StopDashes`
      - "start dashes 'cresc.'", "stop dashes"
    * - Trill
      - :class:`~scamp.spanners.StartTrill`, :class:`~scamp.spanners.StopTrill`
      - "start trill", "start trill flat", "stop trill"
    * - Piano pedal
      - :class:`~scamp.spanners.StartPedal`, :class:`~scamp.spanners.ChangePedal`, :class:`~scamp.spanners.StopPedal`
      - "start pedal", "change pedal", "stop pedal"

Spanner Labels
~~~~~~~~~~~~~~

Lastly, it may on occasion be necessary to distinguish between multiple spanners of the same type. For example,
the following is ambiguous:

.. code-block:: python3

    inst.play_note(60, 1, 0.5, "start slur")
    inst.play_note(64, 1, 0.5, "start slur")
    inst.play_note(62, 1, 0.5, "stop slur")
    inst.play_note(66, 1, 0.5, "stop slur")

Is it one slur inside of another slur, or two overlapping slurs? To specify which you mean, you can use
a label. In string shorthand, this is done with a hashtag

.. code-block:: python3

    inst.play_note(60, 1, 0.5, "start slur #OUTER")
    inst.play_note(64, 1, 0.5, "start slur #INNER")
    inst.play_note(62, 1, 0.5, "stop slur #INNER")
    inst.play_note(66, 1, 0.5, "stop slur #OUTER")

On the other hand all spanner objects have a label argument. The following is equivalent:

.. code-block:: python3

    inst.play_note(60, 1, 0.5, StartSlur(label="OUTER"))
    inst.play_note(64, 1, 0.5, StartSlur(label="INNER"))
    inst.play_note(62, 1, 0.5, StopSlur(label="INNER"))
    inst.play_note(66, 1, 0.5, StopSlur(label="OUTER"))

NOTE: At this time, LilyPond does not allow multiple spanners of the same time in the same voice
simultaneously, so in practice, labels will only work for MusicXML output. In the special case of
slurs within slurs, however, you can use a regular slur and a phrasing slur.

.. _Dynamics:

Dynamics
--------

You can attach a dynamic to a note in any of the following ways:

.. code-block:: python3

    inst.play_note(60, 1, 1, "p")
    inst.play_note(60, 1, 1, "dynamic: p")
    inst.play_note(60, 1, 1, {"dynamics": ["p"]})

Dynamics can be any of the following: "f", "ff", "fff", "ffff", "fffff", "ffffff", "fp", "fz", "mf", "mp", "p", "pp",
"ppp", "pppp", "ppppp", "pppppp", "rf", "rfz", "sf", "sffz", "sfp", "sfpp", "sfz".

.. _Staff Text:

Staff Text
----------

You can attach text to a note --- such as technique or expressive text --- in any of the following ways:

.. code-block:: python3

    inst.play_note(60, 1, 1, "senza vib.")
    inst.play_note(60, 1, 1, "text: senza vib.")
    inst.play_note(60, 1, 1, {"texts": ["senza vib."]})
    inst.play_note(60, 1, 1, StaffText("senza vib.")

Note that if you don't explicitly state that the string you are providing is text, SCAMP will try to interpret it
as one of the other possible note properties first. For example, the following will get interpreted as a staccato
articulation:

.. code-block:: python3

    inst.play_note(60, 1, 1, "staccato")

To attach the *text* "staccato" to a note, you have to be more explicit, e.g.:

.. code-block:: python3

    inst.play_note(60, 1, 1, "text: staccato")
    inst.play_note(60, 1, 1, StaffText("staccato"))

Bold and Italics
~~~~~~~~~~~~~~~~

You can make the text bold or italic in a couple of different ways. The first is to use
a :class:`scamp.text.StaffText` object:

.. code-block:: python3

    inst.play_note(60, 1, 1, StaffText("with emphasis", italic=True))
    inst.play_note(60, 1, 1, StaffText("boldly", bold=True))
    inst.play_note(60, 1, 1, StaffText("very boldly", italic=True, bold=True)

Alternatively, you can use markdown syntax for this effect

.. code-block:: python3

    inst.play_note(60, 1, 1, "*with emphasis*")
    inst.play_note(60, 1, 1, "**boldly**")
    inst.play_note(60, 1, 1, "***very boldly***")

Note, however, that this will only work on the entire text, not on individual words, and that other markdown syntax is
not supported.

Staff Placement
~~~~~~~~~~~~~~~

By default, text is placed above the staff. To place it below the staff, you have to use a :class:`~scamp.text.StaffText`
object:

.. code-block:: python3

    inst.play_note(60, 1, 1, StaffText("cresc.", italic=True, placement="below"))

.. _Playback Adjustments:

Playback Adjustments
--------------------

Sometimes, you want the playback of a note to differ from its notation. For example, a diamond notehead might represent
a harmonic which should sound an octave (or some other interval) higher than notated. You can use the note properties
argument to do this:

.. code-block:: python3

    inst.play_note(60, 1, 1, "notehead: diamond, pitch + 12")

The string shorthand "pitch + 12" is equivalent to `NotePlaybackAdjustment.add_to_params(pitch=12)`. You can pass a
:class:`~scamp.playback_adjustments.NotePlaybackAdjustment` directly instead if you want:

.. code-block:: python3

    inst.play_note(60, 1, 1, ["notehead: diamond", NotePlaybackAdjustment.add_to_params(pitch=12)])

In addition to pitch, volume and length can also be adjusted, and in each case you can do addition/subtraction,
multiplication, or direct setting to a value. For example, to increase the volume of a note by a factor of 1.2 and
set its playback length to 2.5, you could do:

.. code-block:: python3

    inst.play_note(60, 1, 1, "volume * 1.2, length = 2.5")

These alterations could also be accomplished using :func:`~scamp.playback_adjustments.NotePlaybackAdjustment.scale_params`
or :func:`~scamp.playback_adjustments.NotePlaybackAdjustment.set_params`.

Note that changing note playback length does *not* change how long the `play_note` call blocks for. This is useful, for
instance, if we want to create a legato effect, in which each note overlaps with the next:

.. code-block:: python3

    for p in range(60, 70):
        inst.play_note(p, 1, 0.5, "length * 1.2")

Time-Varying Playback Adjustments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lastly, it's possible to use a list or :class:`expenvelope.envelope.Envelope` in a playback adjustment to create a
time-varying modification. For example, the following would play three notes with a forte-piano effect:

.. code-block:: python3

    forte_piano_effect = NotePlaybackAdjustment.scale_params(volume=Envelope([1, 0.3], [0.2]))
    inst.play_note(60, 0.5, 3, forte_piano_effect)
    inst.play_note(60, 0.7, 3, forte_piano_effect)
    inst.play_note(60, 1.0, 3, forte_piano_effect)

In the first note, e.g., the actual volume played would start at 0.5 and drop down to 0.15, since we're using a playback
adjustment that scales the original volume.

You can also use lists, which will get interpreted as envelopes, e.g.:

.. code-block:: python3

    inst.play_note(60, 1.0, 4, "pitch + [0, 1, -1, 0]")

However, it should be noted that, by default, SCAMP stretches the resulting envelope to last for the duration of the
note. This might not be desired in the case of the forte-piano effect above, where you want a crisp diminuendo, even
for a long note.

.. _Spelling Policy:

Spelling Policy
---------------

A :class:`scamp.spelling.SpellingPolicy` specifies how each pitch class should be spelled. (For example, MIDI pitch 61
could be spelled as a C# or a Db.) While you can set a default spelling policy for the whole session or for an
individual part, you can also specify spelling on an individual note basis using the properties argument.

The following are equivalent:

.. code-block:: python3

    inst.play_note(66, 1.0, 1, SpellingPolicy.from_circle_of_fifths_position(2))
    inst.play_note(66, 1.0, 1, "key: D")
    inst.play_note(66, 1.0, 1, "spelling: G lydian")
    inst.play_note(66, 1.0, 1, "D major")

Spelling policy strings are interpreted according to :func:`scamp.spelling.SpellingPolicy.from_string`. If you want
to directly specify whether a note should be spelled as a sharp or flat (rather than give a key signature), you can
use the string "#" or "b":

.. code-block:: python3

    inst.play_note(61, 1.0, 1, "b")
    inst.play_note(61, 1.0, 1, "#")

.. _Voices:

Voices
------

You can use the note properties argument to specify which voice a note should be placed in within a single staff. For
example, this code:

.. code-block:: python3

    inst.play_note(62, 0.5, 0.5, "voice: 1")
    inst.play_note(60, 0.5, 0.5, "voice: 2")
    inst.play_note(58, 0.5, 0.5, "voice: 2")
    inst.play_note(62, 0.5, 0.5, "voice: 2")
    inst.play_note(64, 0.5, 0.5, "voice: 1")
    inst.play_note(62, 0.5, 0.5, "voice: 2")
    inst.play_note(60, 0.5, 0.5, "voice: 2")
    inst.play_note(64, 0.5, 0.5, "voice: 2")

...produces the notation:

.. image:: VoicesExample.png
  :width: 400
  :alt: Using properties to place notes in different voices
  :align: center

You can also use named voices, which get converted to numbered voices before exporting to notation. In the following
example, the named voice "top_notes" gets assigned to voice 1, since it is the first available voice, while
"bottom_notes" gets assigned to voice 2. The notational result is the same as the previous example.

.. code-block:: python3

    inst.play_note(62, 0.5, 0.5, "voice: top_notes")
    inst.play_note(60, 0.5, 0.5, "voice: bottom_notes")
    inst.play_note(58, 0.5, 0.5, "voice: bottom_notes")
    inst.play_note(62, 0.5, 0.5, "voice: bottom_notes")
    inst.play_note(64, 0.5, 0.5, "voice: top_notes")
    inst.play_note(62, 0.5, 0.5, "voice: bottom_notes")
    inst.play_note(60, 0.5, 0.5, "voice: bottom_notes")
    inst.play_note(64, 0.5, 0.5, "voice: bottom_notes")

Using named voices like this can be useful when the goal is to keep musically related material together in the same
voice, bue the exact number of the voice is not important.

.. _Extra Playback Parameters:

Extra Playback Parameters
-------------------------

In addition to pitch and volume, you can use SCAMP to control other parameters of sound, so long as your playback
implementation knows how to make sense of it. For example, when you play notes via OSC messages to an external
synthesizer (e.g. via :func:`~scamp.session.Session.new_osc_part`), you can use extra playback parameters to send
OSC messages controlling vibrato, brightness of timbre, or any other aspect of sound production. The way we do this
is through the properties argument. For example, the following will play a note with a vibrato frequency of 7 and a
brightness that gradually diminishes from 1 to 0.

.. code-block:: python3

    inst.play_note(62, 0.5, 5, "param_vibrato: 7, param_brightness: [1, 0]")

Note that the list [1, 0] gets converted into an :class:`~expenvelope.envelope.Envelope` that lasts for the same
duration as the note itself. If we're using an OSC part, this will result in messages of the form
`instrument_name/change_parameter/vibrato` getting sent to the receiving synthesizer.

Although the above approach is probably the easiest way to set additional playback parameters, either of the following
will have an equivalent effect:

.. code-block:: python3

    inst.play_note(62, 0.5, 5, {"param_vibrato": 7, "param_brightness": [1, 0]})
    inst.play_note(62, 0.5, 5, {"extra_playback_parameters": {"vibrato": 7, "brightness": [1, 0]}})

Ultimately, whichever way you do it, SCAMP ultimately converts it to the latter form.

Using Extra Parameters for MIDI CC
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Although the default playback implementation in SCAMP uses the MIDI protocol to play notes using soundfonts, and
therefore can't understand parameters like brightness, you can use the extra playback parameters to send MIDI CC
messages. When the playback implementation uses MIDI, SCAMP interprets any parameter name that is an integer between
0 and 127 as a control change. Not,e however, that all of the values given should be in the range from 0 to 1, which
gets translated to a range from 0 to 127.

For example, since MIDI CC 10 controls pan, the following will play a note from the left speaker, a note from the 
right speaker, and then a note that oscillates between left and right:

.. code-block:: python3

    violin.play_note(70, 0.8, 2, "param_10: 0")
    violin.play_note(71, 0.8, 2, "param_10: 1")
    violin.play_note(70, 0.8, 15, "param_10: [0, 1, 0, 1, 0, 1]")

