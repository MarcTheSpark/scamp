# SCAMP Examples Index

<!-- GENERATED FILE - do not edit. Regenerate with: python3 regenerate_index.py -->

A map of every example in this folder, for humans and AI assistants alike. The directory
layout is the organization: each top-level folder (besides `Tutorial/`) is a topic, and the
folders within it are sections. An example is one script, or one sub-folder of scripts.
Order within a folder is set by its `docs_order.txt`; an example may be cross-listed under
several sections by referencing its path there. Paths are relative to `scamp/examples/`.

**To add an example:** drop the script (or folder) into the right section folder. To place
or order it, add its name to that folder's `docs_order.txt` (unlisted examples sort to the
end); to cross-list it elsewhere, add its path to another section's `docs_order.txt`.


## Tutorial

The curated teaching set -- work through it in order.

- **Hello World** — `Tutorial/01_hello_world.py`
  <br>Plays a C major arpeggio. — *API:* `Session`, `new_part`, `play_note`
- **Tempo Change** — `Tutorial/02_tempo_change.py`
  <br>Same as Hello World example, but repeatedly, with changing tempi. — *API:* `Moment`, `Session`, `new_part`, `play_note`, `set_tempo_target` — *also under:* Time & clocks › Setting & changing tempo
- **Blocking False** — `Tutorial/03_blocking_false.py`
  <br>By default `play_note` blocks execution until the note is done playing. This is very useful for playing a melody, since you simply call `play_note` in sequence for every note of the melody. However, one simple way of allowing notes to overlap — if desired — is to pass the keyword argument `blocking=False`. This is essentially a single-note fork: playback continues on to the next line without waiting for the note to finish. — *API:* `Session`, `new_part`, `play_note`, `wait`, `wait_for_children_to_finish` — *also under:* Time & clocks › Forking & simultaneity
- **Play Chord** — `Tutorial/04_play_chord.py`
  <br>Demonstrates `ScampInstrument.play_chord` by playing a famous progression, and then playing it a few more times randomly up and down the keyboard. — *API:* `Moment`, `ScampInstrument`, `Session`, `new_part`, `play_chord`, `set_tempo_target` — *also under:* Time & clocks › Forking & simultaneity
- **Random Durations and Rests** — `Tutorial/05_random_durations_and_rests.py`
  <br>Loops a C major arpeggio twice, but with random, floating-point durations. Also sometimes adds a rest of up to a second between notes. — *API:* `Session`, `new_part`, `play_note`, `wait`
- **Generating Notation** — `Tutorial/06_notation.py`
  <br>Plays a simple C Major arpeggio, and generates notation for it. — *API:* `Performance`, `Score`, `Session`, `new_part`, `play_note`, `print_lilypond`, `start_transcribing`, `to_score` — *also under:* Notation & engraving › Basics
- **Time Signatures** — `Tutorial/07_time_signature.py`
  <br>Plays a simple C Major arpeggio, and generates notation for it in three different ways: - with a 3/8 time signature - with a 3/8 time signature for the first measure followed by 2/4 - with alternating 3/8 and 2/4 time signatures - with a list of bar lengths determining time signatures — *API:* `Score`, `Session`, `new_part`, `play_note`, `start_transcribing`, `to_score` — *also under:* Notation & engraving › Basics
- **Quantization of Random Floating-Point Durations** — `Tutorial/08_random_quantized.py`
  <br>Similar to the "Random Durations and Rests" example, except that now we generate notation. Since the lengths are floating point, quantization occurs in the call to "to_score" — *API:* `Session`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait` — *also under:* Notation & engraving › Quantization
- **Simplified Quantization** — `Tutorial/09_simplified_quantization.py`
  <br>Same as last example except that we see two different levers for simplifying the notation: `max_divisor` (which defaults to 8) sets a hard cap on how finely we can divide the beat. `simplicity_preference` (which defaults to 2), rather than setting a hard cap, amplifies the error calculation for complicated divisors, leading to simpler beat divisions unless the complicated division is a very good match. — *API:* `Session`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait` — *also under:* Notation & engraving › Quantization
- **Multi-Part Music** — `Tutorial/10_multi_part.py`
  <br>Plays two coordinated but independent parallel parts, one for oboe and one for bassoon. — *API:* `Session`, `fork`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait_for_children_to_finish` — *also under:* Time & clocks › Forking & simultaneity
- **Nested Tempi** — `Tutorial/11_nested_tempi`
  <br>Music running with nested tempi: a trombone plays a cyclic quarter-note pattern on the session's accelerating pulse, while a trumpet, forked onto a child clock, plays a similar eighth-note pattern. After a few beats, while the overall session is still accelerating, the trumpet clock starts decelerating to half speed. The music is then notated two ways: nested_tempi.py transcribes from the session's point of view so that the trombone plays straight quarter notes, while the trumpet shows a written-out deceleration from eighth to quarter notes; nested_tempi_child_clock.py records from the trumpet clock's point of view, yielding plain eighth notes in the trumpet and more complex rhythmic notation in the trombone. — *API:* `Clock`, `MetricPhaseTarget`, `Moment`, `Session`, `fork`, `new_part`, `play_note`, `set_rate_target`, `set_tempo_target`, `start_transcribing`, `to_score` — *also under:* Time & clocks › Advanced
- **Envelopes (basic)** — `Tutorial/12_envelopes_basic.py`
  <br>Create and plot two simple envelopes, one with evenly-spaced linear segments, and one with uneven, curved segments. — *API:* `Envelope`, `from_levels`, `show_plot` — *also under:* Envelopes › Construction
- **Envelopes (advanced)** — `Tutorial/13_envelopes_advanced.py`
  <br>A more comprehensive list of ways to construct and modify Envelopes. — *API:* `Envelope`, `adsr`, `append_envelope`, `ar`, `asr`, `from_function`, `from_levels`, `from_levels_and_durations`, `from_list`, `from_points`, `prepend_envelope`, `release`, `...` — *also under:* Envelopes › Construction
- **Glissando from Envelope** — `Tutorial/14_gliss_from_envelope.py`
  <br>Plays a glissando by passing an Envelope to the pitch parameter of play_note. — *API:* `Envelope`, `Session`, `new_part`, `play_note`, `start_transcribing`, `to_score` — *also under:* Pitch › Glissando, Envelopes › As note parameters
- **Envelope Shorthand** — `Tutorial/15_envelope_shorthand.py`
  <br>Plays two glissandi by passing lists instead of envelopes to the pitch argument of play_note. — *API:* `Envelope`, `Session`, `new_part`, `play_note`, `start_transcribing`, `to_score` — *also under:* Pitch › Glissando, Envelopes › As note parameters
- **Start and End Note** — `Tutorial/16_start_and_end_note.py`
  <br>Plays notes by calling start_note (or start_chord) and then manipulating them afterward, instead of defining the course of the note from the beginning with "play_note". The "start_note" and "start_chord" functions return handles that can be used to change the pitch, volume or other parameters of the note after they have started, as well as end the note. — *API:* `Session`, `change_pitch`, `change_volume`, `end`, `new_part`, `start_chord`, `start_note`, `start_transcribing`, `to_score`, `wait` — *also under:* Playback › Note handles
- **Volume Envelope** — `Tutorial/17_volume_envelope.py`
  <br>Plots an envelope representing a forte-piano-crescendo dynamic, and then uses it to affect the dynamics of a note's playback. This example shows that an Envelope can be passed to the volume argument of "play_note", just like it can to the pitch argument. (The list short-hand also works, by the way.) — *API:* `Envelope`, `Session`, `new_part`, `play_note`, `show_plot` — *also under:* Envelopes › As note parameters
- **Microtonal Playback and Notation** — `Tutorial/18_microtonal.py`
  <br>Plays a few microtonal chords and notates them, turning on exact microtonal annotations. — *API:* `Session`, `new_part`, `play_chord`, `start_transcribing`, `to_score` — *also under:* Pitch › Scales & microtonality, Notation & engraving › Special notations
- **Playback Implementations** — `Tutorial/19_playback_implementations.py`
  <br>Shows how to create parts that use different implementations for playback. This assumes that you are connecting to a midi device on port zero. — *API:* `MIDIStreamPlaybackImplementation`, `OSCPlaybackImplementation`, `PlaybackImplementation`, `Session`, `SoundfontPlaybackImplementation`, `add_osc_playback`, `add_streaming_midi_playback`, `new_midi_part`, `new_osc_part`, `new_part`, `new_silent_part`, `play_note`, `...` — *also under:* Playback › Playback implementations
- **Note Properties** — `Tutorial/20_note_properties.py`
  <br>Shows how the fourth (optional) properties argument to "play_note" can be used to affect other aspects of playback and notation, such as articulation and noteheads. All properties are ultimately converted into a NotePropertiesDictionary; If a string is given, it is parsed into key / value pairs. In many cases, e.g. with "staccato" below, SCAMP can infer that it is referring to an articulation. — *API:* `Envelope`, `NotePlaybackAdjustment`, `NoteProperties`, `Session`, `beat`, `new_part`, `play_chord`, `play_note`, `start_transcribing`, `to_score` — *also under:* Notation & engraving › Special notations, Playback › Playback adjustments
- **Pitch Spelling** — `Tutorial/21_pitch_spelling.py`
  <br>Demonstrates the ability to define note pitch spelling using the optional properties argument to "play_note". This can be done by explicitly setting it, or by defining the key in which it resides. — *API:* `Session`, `new_part`, `play_chord`, `play_note`, `start_transcribing`, `to_score` — *also under:* Pitch › Pitch spelling
- **Staff Text** — `Tutorial/22_staff_text.py`
  <br>Demonstrates various ways of adding text annotations to notes that are played. Text is one of the various notational details that can be passed to the fourth, optional "properties" argument of play_note. — *API:* `Session`, `Staff`, `StaffText`, `new_part`, `play_chord`, `play_note`, `start_transcribing`, `to_score` — *also under:* Notation & engraving › Special notations
- **Special Notations** — `Tutorial/23_special_notations.py`
  <br>Ornaments, tremolo and other single-note notations. These notational details are passed to the fourth, optional "properties" argument of play_note. — *API:* `Envelope`, `NotePlaybackAdjustment`, `Session`, `new_part`, `play_chord`, `play_note`, `start_transcribing`, `to_score` — *also under:* Notation & engraving › Special notations, Playback › Playback adjustments
- **OSC to SuperCollider** — `Tutorial/24_osc_to_supercollider`
  <br>Playing back notes by sending OSC messages to the SuperCollider, which receives them and spawns Synths in response. Start SuperCollider and run the code blocks in `receive_from_supercollider.scd`, then run `osc_to_supercollider.py`. Note that the easy way to receive note events from SCAMP in SuperCollider specifically is with the ScampUtils quark, as demonstrated by `receive_from_supercollider_scamputils.scd`. — *API:* `Envelope`, `Session`, `ar`, `new_osc_part`, `num_notes_playing`, `play_note`, `start_transcribing`, `to_score`, `wait` — *also under:* Playback › Playback implementations
- **Live MIDI input and output** — `Tutorial/25_MIDI_in_out.py`
  <br>Demonstration of receiving and sending live midi input to and from a midi keyboard. Every note received by the keyboard is immediately sent back to the keyboard a perfect fifth higher. — *API:* `Session`, `end`, `new_midi_part`, `print_available_midi_output_devices`, `register_midi_listener`, `start_note`, `wait_forever` — *also under:* Interactivity & visualization › MIDI input
- **Computer Keyboard Input** — `Tutorial/26_keyboard_input.py`
  <br>(WARNING: consumes key events and makes the keyboard otherwise unresponsive. To avoid this, you can remove the suppress=True flag under register_keyboard_listener) Demonstration of receiving computer keyboard events and using them to play notes based on the key number. Any key whose number code lies within a reasonable range triggers the playback of a note of that MIDI pitch. — *API:* `Session`, `end`, `new_part`, `register_keyboard_listener`, `start_note`, `wait_forever` — *also under:* Interactivity & visualization › Keyboard input
- **Mouse Input** — `Tutorial/27_mouse_input.py`
  <br>(WARNING: consumes mouse events and makes the mouse otherwise unresponsive. To avoid this, you can remove the suppress=True flag under register_mouse_listener) Demonstration of receiving computer mouse events and using them to play notes based on x and y position. Notes are started on mouse down and released on mouse up.  Left click plays a piano note, and right click plays a flute note. X position controls pitch, Y controls volume. By moving the mouse after clicking, the pitch can be bent up and down and the volume can be changed. — *API:* `Session`, `change_pitch`, `change_volume`, `end`, `new_part`, `register_mouse_listener`, `start_note`, `wait_forever` — *also under:* Interactivity & visualization › Mouse input
- **OSC Listening** — `Tutorial/28_osc_listening`
  <br>Run `osc_listener.py` first, which uses Session.register_osc_listener to listen for OSC messages and play back notes and horrific bagpipe clusters. Then run `osc_sender.py` which simulates an external program sending OSC messages to to the listener script, leading to the aforementioned notes and horrific bagpipe clusters. — *API:* `Session`, `new_part`, `play_chord`, `play_note`, `register_osc_listener`, `split`, `wait_forever`
- **Spanners** — `Tutorial/29_spanners.py`
  <br>Demonstration of starting and stopping various spanners, such as slurs, hairpins, trills, brackets, and pedal lines. Note that there is some finickiness with both lilypond and MusicXML output. LilyPond does not allow multiple of the same spanner at the same time (at least in the same voice), whereas MusicXML does. If exporting to MusicXML, you can keep the spanners straight by providing a label. On the other hand, implementations of MusicXML in many notation programs mangle spanner input. So there's that. — *API:* `Session`, `StartSlur`, `StopSlur`, `fork`, `new_part`, `play_chord`, `play_note`, `start_transcribing`, `time`, `to_score` — *also under:* Notation & engraving › Special notations

## Time & clocks


### Forking & simultaneity

- Multi-Part Music — *(home: `Tutorial/10_multi_part.py`)*
- Blocking False — *(home: `Tutorial/03_blocking_false.py`)*
- Play Chord — *(home: `Tutorial/04_play_chord.py`)*
- **Chords and Noteheads** — `Time & clocks/Forking & simultaneity/chords_example.py`
  <br>Chords with per-note noteheads, and a start_chord handle whose pitches change over time. Under the hood, `play_chord` plays all but one of its notes with `blocking=False` and the last one blocking, so the notes sound together. — *API:* `Session`, `change_pitch`, `end`, `new_part`, `play_chord`, `start_chord`, `start_transcribing`, `to_score`, `wait` — *also under:* Playback › Note handles
- Voice Leading / spelling policy — *(home: `Pitch/Pitch spelling/voice_leading.py`)*
- **Guitar Arpeggios** — `Time & clocks/Forking & simultaneity/guitar_arpeggios.py`
  <br>Fingerpicking-style guitar arpeggios built from overlapping held notes. — *API:* `Session`, `new_part`, `play_note`, `wait`
- **Octave Lines** — `Time & clocks/Forking & simultaneity/octave_lines.py`
  <br>A short passage of random notes for violin and piano, which uses the optional note properties argument to `play_note` to apply ottava when notes are very high or very low. The two parts run as parallel forked processes, an example of multi-part playback using `fork`. — *API:* `Session`, `fork`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait`, `wait_for_children_to_finish`

### Setting & changing tempo

- Tempo Change — *(home: `Tutorial/02_tempo_change.py`)*
- Piano Phase — *(home: `Composition & form/Larger-scale form/reich_piano_phase.py`)*
- Evolving Form — *(home: `Composition & form/Larger-scale form/evolving_form`)*

### Advanced

- Nested Tempi — *(home: `Tutorial/11_nested_tempi`)*
- **Metric Phase** — `Time & clocks/Advanced/metric_phase.py`
  <br>Rate targets aligned to metric phase, so accelerations and decelerations land on downbeats. — *API:* `MetricPhaseTarget`, `Moment`, `Session`, `current_clock`, `fork`, `kill`, `new_part`, `play_note`, `set_rate_target`, `set_rate_targets`, `start_transcribing`, `to_score`, `...`

## Pitch


### Scales & microtonality

- **Scales** — `Pitch/Scales & microtonality/scale_example`
  <br>Demo of the scamp_extensions Scale object, a highly flexible representation of a scale that can be indexed into infinitely in both directions from a root note. Scales can be microtonal (and even loaded from a scala file), and are constructed from intervals that can be expressed as either a frequency ratio, a distance in cents, or a combination of the two. Scales can also be transposed and modally rotated. — *API:* `Session`, `new_part`, `play_chord`, `play_note`
- Microtonal Playback and Notation — *(home: `Tutorial/18_microtonal.py`)*

### Pitch spelling

- Pitch Spelling — *(home: `Tutorial/21_pitch_spelling.py`)*
- **Voice Leading / spelling policy** — `Pitch/Pitch spelling/voice_leading.py`
  <br>Rule-based four-part voice leading over a scale, spelled in E major via the `default_spelling_policy` argument. — *API:* `Session`, `Voice`, `new_part`, `play_chord`, `play_note`, `start_transcribing`, `to_score` — *also under:* Time & clocks › Forking & simultaneity

### Glissando

- Glissando from Envelope — *(home: `Tutorial/14_gliss_from_envelope.py`)*
- Envelope Shorthand — *(home: `Tutorial/15_envelope_shorthand.py`)*

## Envelopes


### Construction

- Envelopes (basic) — *(home: `Tutorial/12_envelopes_basic.py`)*
- Envelopes (advanced) — *(home: `Tutorial/13_envelopes_advanced.py`)*

### As note parameters

- Glissando from Envelope — *(home: `Tutorial/14_gliss_from_envelope.py`)*
- Volume Envelope — *(home: `Tutorial/17_volume_envelope.py`)*
- Envelope Shorthand — *(home: `Tutorial/15_envelope_shorthand.py`)*

### As compositional parameters

- Evolving Form — *(home: `Composition & form/Larger-scale form/evolving_form`)*
- TimeVaryingParameter — *(home: `Composition & form/Larger-scale form/time_varying_parameter_example.py`)*

## Notation & engraving


### Basics

- Generating Notation — *(home: `Tutorial/06_notation.py`)*
- Time Signatures — *(home: `Tutorial/07_time_signature.py`)*
- **Export to MIDI File** — `Notation & engraving/Basics/record_and_export_midi.py`
  <br>Records glissandi with microtonal pitches and playback params (fast-forwarded), then exports the performance as a MIDI file. — *API:* `Envelope`, `Moment`, `Session`, `export_to_midi_file`, `fast_forward`, `fork`, `kill`, `new_part`, `play_note`, `set_rate_target`, `start_transcribing` — *also under:* Playback › MIDI CC & arbitrary parameters

### Quantization

- Quantization of Random Floating-Point Durations — *(home: `Tutorial/08_random_quantized.py`)*
- Simplified Quantization — *(home: `Tutorial/09_simplified_quantization.py`)*
- **Quantization Comparison** — `Notation & engraving/Quantization/quantization.py`
  <br>Records a loose piano improvisation against a metronome, then plays back the quantized version. — *API:* `MeasureQuantizationScheme`, `QuantizationScheme`, `Session`, `fork`, `new_part`, `play`, `play_chord`, `play_note`, `quantized`, `start_transcribing`, `wait`
- Piano Phase — *(home: `Composition & form/Larger-scale form/reich_piano_phase.py`)*

### Special notations

- Note Properties — *(home: `Tutorial/20_note_properties.py`)*
- Staff Text — *(home: `Tutorial/22_staff_text.py`)*
- Special Notations — *(home: `Tutorial/23_special_notations.py`)*
- Spanners — *(home: `Tutorial/29_spanners.py`)*
- **Multiple Voices** — `Notation & engraving/Special notations/voices.py`
  <br>Demonstration of how to place notes in specific voices within a staff/part. Named voices keep notes together in the same voice, and numbered voices determine exactly which voice they go in. By default SCAMP allows up to four voices per staff, but this can easily become quite messy. Set `engraving_settings.max_voices_per_staff` to limit the number of voices per staff, placing overflow voices on separate staves. — *API:* `Session`, `fork`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait`, `wait_for_children_to_finish`
- **Multiple Voices with Octave Lines** — `Notation & engraving/Special notations/voices_with_octave_lines.py`
  <br>Same as the voices example, but with ottava applied to certain voices. These ottava contradict one another when the voices are (by default) placed on the same staff, so the largest octave line wins and a warning is emitted. To avoid this conflict, set `engraving_settings.max_voices_per_staff = 1` to place each voice in a separate staff. — *API:* `Session`, `fork`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait`, `wait_for_children_to_finish`
- Microtonal Playback and Notation — *(home: `Tutorial/18_microtonal.py`)*
- **Performance Post-Processing** — `Notation & engraving/Special notations/post_processing.py`
  <br>Post-processes a recorded Performance of a random walk of thirds and fifths, so that every time three consecutive notes are a triad, they are slurred together and spelled consistently. — *API:* `Performance`, `Session`, `SpellingPolicy`, `StartSlur`, `StopSlur`, `get_note_iterator`, `new_part`, `play_note`, `start_transcribing`, `to_score`

### Abjad & pymusicxml tweaks

- **Key Signature via pymusicxml** — `Notation & engraving/Abjad & pymusicxml tweaks/key_sig.py`
  <br>Adds a key signature by exporting through pymusicxml and setting it on the first measure. — *API:* `Session`, `new_part`, `play_note`, `start_transcribing`, `to_music_xml`, `to_score`
- **Double Score** — `Notation & engraving/Abjad & pymusicxml tweaks/double_score.py`
  <br>Records two performances, turns them into scores, renders to abjad, and sticks them together! — *API:* `Score`, `Session`, `fork`, `new_part`, `play_note`, `start_transcribing`, `to_abjad`, `to_score`, `wait_for_children_to_finish`

### From live input

- **Computer Keyboard Input** — `Notation & engraving/From live input/keyboard_input_with_notation.py`
  <br>(WARNING: consumes key events and makes the keyboard otherwise unresponsive. To avoid this, you can remove the suppress=True flag under register_keyboard_listener) Demonstration of receiving computer keyboard events and using them to play notes based on the key number. Any key whose number code lies within a reasonable range triggers the playback of a note of that MIDI pitch. Escape — *API:* `Session`, `end`, `fork`, `kill`, `new_part`, `play_note`, `register_keyboard_listener`, `start_note`, `start_transcribing`, `to_score`, `wait_forever` — *also under:* Interactivity & visualization › Keyboard input
- **Run as Server and Render Scores** — `Notation & engraving/From live input/run_as_server_render_scores.py`
  <br>Runs the session as a server, repeatedly recording short fragments and popping up a score for each. — *API:* `Score`, `Session`, `fork`, `new_part`, `play_note`, `run_as_server`, `start_transcribing`, `to_score`

## Playback


### Playback implementations

- Playback Implementations — *(home: `Tutorial/19_playback_implementations.py`)*
- OSC to SuperCollider — *(home: `Tutorial/24_osc_to_supercollider`)*
- **OSC Instrument Playback** — `Playback/Playback implementations/osc_playback`
  <br>Uses a new_osc_part to send messages to a running SuperCollider script at OSCListenerPython.scd. To test out, run all the code blocks in OSCListenerPython.scd, make sure that the port below matches the result of NetAddr.langPort, and then run this script. — *API:* `Session`, `fork`, `new_osc_part`, `play_note`, `wait`, `wait_forever`
- **MultiPresetInstrument** — `Playback/Playback implementations/multipreset_example.py`
  <br>Demo of the MultiPresetInstrument, a convenience meta-instrument for subsuming several different playing techniques and their associated notations under a single instrument interface. — *API:* `ScampInstrument`, `Session`, `change_pitch`, `end`, `play_note`, `start_note`, `start_transcribing`, `to_score`, `wait`

### Note handles

- Start and End Note — *(home: `Tutorial/16_start_and_end_note.py`)*
- Chords and Noteheads — *(home: `Time & clocks/Forking & simultaneity/chords_example.py`)*

### Playback adjustments

- Note Properties — *(home: `Tutorial/20_note_properties.py`)*
- Special Notations — *(home: `Tutorial/23_special_notations.py`)*

### MIDI CC & arbitrary parameters

- Export to MIDI File — *(home: `Notation & engraving/Basics/record_and_export_midi.py`)*
- **Max Sender (monophonic)** — `Playback/MIDI CC & arbitrary parameters/scamp_to_max_monophonic`
  <br>Sends monophonic notes with an extra playback parameter over OSC to Max. See the accompanying Max patch, which shows how to receive and route those messages. — *API:* `Session`, `new_osc_part`, `play_note`, `wait`
- **Max Sender (polyphonic)** — `Playback/MIDI CC & arbitrary parameters/scamp_to_max_polyphonic`
  <br>Sends overlapping glissando notes over OSC to Max. See the accompanying Max patch, which receives and routes those messages using a poly object. — *API:* `Session`, `new_osc_part`, `play_note`, `wait`

### Other

- **Save and Load a Performance** — `Playback/Other/save_and_load_performance`
  <br>Contains two scripts: One that plays some music and records a portion of that music to a JSON file, and a second that reads the JSON file and plays the recorded performance repeatedly while accelerating. — *API:* `Ensemble`, `Envelope`, `Moment`, `Performance`, `Session`, `fork`, `get_beat`, `new_part`, `play`, `play_note`, `set_tempo_target`, `start_transcribing`, `...`

## Interactivity & visualization


### Keyboard input

- Computer Keyboard Input — *(home: `Tutorial/26_keyboard_input.py`)*
- Computer Keyboard Input — *(home: `Notation & engraving/From live input/keyboard_input_with_notation.py`)*
- **Key Plane** — `Interactivity & visualization/Keyboard input/key_plane_example.py`
  <br>Maps the computer keyboard onto a 2D grid of pitches with scamp_extensions' KeyPlane; each key press starts a flute note whose pitch and volume come from its row and column. — *API:* `Session`, `end`, `new_part`, `start_note`

### Mouse input

- Mouse Input — *(home: `Tutorial/27_mouse_input.py`)*
- Indispensability — *(home: `Composition & form/Algorithmic approaches/indispensibility_example.py`)*

### MIDI input

- Live MIDI input and output — *(home: `Tutorial/25_MIDI_in_out.py`)*
- **MIDI Keyboard Mapper** — `Interactivity & visualization/MIDI input/midi_keyboard_mapper.py`
  <br>A script written at the request of Paul Timmermans, in which different pitches or ranges of pitches on the keyboard can be mapped to particular instruments and chords. The heart of the script is the dictionary `pitch_to_instrument_and_pitches`, which expresses, for each key, which pitches and on which instrument should be played. — *API:* `Session`, `end`, `new_midi_part`, `new_part`, `print_available_midi_input_devices`, `print_available_midi_output_devices`, `register_midi_listener`, `split`, `start_chord`, `start_note`, `wait_forever`

### Responding to a GUI

- **Qt Interactive** — `Interactivity & visualization/Responding to a GUI/qt_interactive.py`
  <br>A draggable PyQt rectangle drives live playback in a server session. Moving the rectangle fires a callback that sets the tempo of the clock running the note loop; its vertical position still sets the pitch. — *API:* `Envelope`, `Session`, `fork`, `new_part`, `play_note`, `run_as_server`, `start_transcribing`, `to_score`, `value_at`

### Visualization

- Conway's Game of Life (pygame version) — *(home: `Composition & form/Algorithmic approaches/conway.py`)*
- Barlicity — *(home: `Composition & form/Larger-scale form/evanstein_barlicity.py`)*
- Leaf Loops — *(home: `Composition & form/Larger-scale form/leaf_loops.py`)*

## Composition & form


### Algorithmic approaches

- **Conway's Game of Life (pygame version)** — `Composition & form/Algorithmic approaches/conway.py`
  <br>Conway's Game of Life sonified, with a pygame window used for visualization instead of matplotlib. Original by Raphael Radna; visualization ported to pygame. — *API:* `Clock`, `Session`, `end`, `new_part`, `start_note` — *also under:* Interactivity & visualization › Visualization
- **L-System** — `Composition & form/Algorithmic approaches/l_system_example.py`
  <br>Example usage of the from :class:`~scamp_extensions.process.l_system.LSystem` class, which allows you to set a vocabulary of symbols, set their rewrite rules and meanings, and evolve and play the resulting L-System. — *API:* `Session`, `fork`, `new_part`, `play_note`, `wait`, `wait_for_children_to_finish`
- **Indispensability** — `Composition & form/Algorithmic approaches/indispensibility_example.py`
  <br>Mouse position controls a rhythmic texture based on Barlow's beat indispensability (barlicity extension). — *API:* `Session`, `change_pitch`, `end`, `new_part`, `play_note`, `register_mouse_listener`, `start_note`, `wait` — *also under:* Interactivity & visualization › Mouse input

### Larger-scale form

- **Leaf Loops** — `Composition & form/Larger-scale form/leaf_loops.py`
  <br>Generative process behind Marc Evanstein's "Leaf Loops" for violin and viola. The shapes, note attack points, and worm shape for several different leaves are found in the LeafPoints directory. — *API:* `Clock`, `Session`, `end_all_notes`, `get_time`, `new_midi_part`, `new_part`, `play_note`, `run_as_server`, `start_note` — *also under:* Interactivity & visualization › Visualization
- **Piano Phase** — `Composition & form/Larger-scale form/reich_piano_phase.py`
  <br>Steve Reich's Piano Phase: the same figure forked at 100 vs. 98 BPM, transcribed on one clock. — *API:* `QuantizationScheme`, `Session`, `fork`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait` — *also under:* Time & clocks › Setting & changing tempo, Notation & engraving › Quantization
- **Barlicity** — `Composition & form/Larger-scale form/evanstein_barlicity.py`
  <br>A large interactive piece built on harmonicity and indispensability (barlicity extension), with multidimensional-scaling visualization in Qt. This was the initial script for the piece, which ultimately became the notated work for piano and electronics that you can view here: https://www.youtube.com/watch?v=xMpET9KKOrw — *API:* `Envelope`, `Session`, `fork`, `get_beat`, `get_time`, `kill`, `new_part`, `play_chord`, `play_note`, `run_as_server`, `send_midi_cc`, `start_transcribing`, `...` — *also under:* Interactivity & visualization › Visualization
- **Evolving Form** — `Composition & form/Larger-scale form/evolving_form`
  <br>A piece for cello, pianoteq (MIDI), and SuperCollider (OSC), shaped by envelope-driven formal parameters. See definitions.py and formal_parameters.py. — *API:* `Envelope`, `Moment`, `Session`, `fork`, `from_levels`, `kill`, `new_midi_part`, `new_osc_part`, `new_part`, `play_chord`, `play_note`, `set_rate_target`, `...` — *also under:* Time & clocks › Setting & changing tempo, Envelopes › As compositional parameters
- **TimeVaryingParameter** — `Composition & form/Larger-scale form/time_varying_parameter_example.py`
  <br>A script using the context-sensitive :class:`~expenvelope.envelope.Envelope` wrapper :class:`TimeVaryingParameter`, which reads into the underlying envelope at the current clock's beat or time when called. — *API:* `Envelope`, `Session`, `current_clock`, `fork`, `from_levels`, `new_part`, `play_note`, `wait_for_children_to_finish` — *also under:* Envelopes › As compositional parameters
- **Lunar Trajectories** — `Composition & form/Larger-scale form/evanstein_lunar_trajectories.py`
  <br>Interactive piano script for the first movement of "Lunar Trajectories". The `notes` list below is a list of all the notes played by the middle arpeggio part in the first movement of the Moonlight Sonata, in order. If a pitch is in that list, then when it is depressed, the piano reacts by playing whichever pitches follow that pitch the first time it occurs in the list. If a pitch is not in the list, then instead we look for the same pitch class but in a different octave, and follow it up by the notes that follow that pitch (transposed back up or down by however many octaves). Every pitch class appears in the first movement, so we don't have the issue of searching for a pitch class that doesn't occur. — *API:* `Session`, `current_clock`, `fork`, `new_midi_part`, `play_note`, `print_available_midi_input_devices`, `print_available_midi_output_devices`, `register_midi_listener`, `send_midi_cc`, `wait`, `wait_forever`

## Non-Python companion files

SuperCollider scripts, Max patches, and saved data used by the examples above:

- `Composition & form/Larger-scale form/LeafPoints/dwarfBirch.json`
- `Composition & form/Larger-scale form/LeafPoints/dwarfBirchAttackPoints.json`
- `Composition & form/Larger-scale form/LeafPoints/dwarfBirchWorm.json`
- `Composition & form/Larger-scale form/LeafPoints/ivy.json`
- `Composition & form/Larger-scale form/LeafPoints/ivyAttackPoints.json`
- `Composition & form/Larger-scale form/LeafPoints/ivyWorm.json`
- `Composition & form/Larger-scale form/LeafPoints/larkSpur.json`
- `Composition & form/Larger-scale form/LeafPoints/larkSpurAttackPoints.json`
- `Composition & form/Larger-scale form/LeafPoints/larkSpurWorm.json`
- `Composition & form/Larger-scale form/evolving_form/Crackler.scd`
- `Playback/MIDI CC & arbitrary parameters/scamp_to_max_monophonic/MonoMain.maxpat`
- `Playback/MIDI CC & arbitrary parameters/scamp_to_max_monophonic/MonoSynth.maxpat`
- `Playback/MIDI CC & arbitrary parameters/scamp_to_max_monophonic/scampreceive.maxpat`
- `Playback/MIDI CC & arbitrary parameters/scamp_to_max_polyphonic/PolyMain.maxpat`
- `Playback/MIDI CC & arbitrary parameters/scamp_to_max_polyphonic/PolySynth.maxpat`
- `Playback/MIDI CC & arbitrary parameters/scamp_to_max_polyphonic/scampreceive.maxpat`
- `Playback/Other/save_and_load_performance/perfShakoboe.json`
- `Playback/Playback implementations/osc_playback/OSCListenerPython.scd`
- `Tutorial/24_osc_to_supercollider/receive_from_supercollider.scd`
- `Tutorial/24_osc_to_supercollider/receive_from_supercollider_scamputils.scd`
