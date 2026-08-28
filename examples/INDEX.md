# SCAMP Examples Index

<!-- GENERATED FILE - do not edit. Regenerate with: python3 regenerate_index.py -->

A map of every example in this folder, for humans and AI assistants alike. Each entry
gives a one-line summary, its feature tags, and the scamp API it exercises. An example is
one script, or one subfolder (several files making a single example). Paths are relative
to `scamp/examples/`.

**How to use it:** scan the *Feature -> examples* section (grouped by domain) to jump to
a topic, then read the per-folder entries for detail. `Tutorial/` is the curated teaching
set -- prefer it for canonical, minimal usage.

**To add an example:** add a script whose docstring ends in a `Tags: comma, separated`
line (nested as `domain/facet`); for a multi-file example, put the summary and tags in the
folder's `about.txt` instead. Then rerun `regenerate_index.py`.


## Feature -> examples

Grouped by domain. Within each entry, `Tutorial/` examples come first.

### basics

`Tutorial/01_hello_world.py`, `Tutorial/02_tempo_change.py`, `Tutorial/04_random_durations_and_rests.py`

### time

- **clocks** — `Tutorial/03_blocking_false.py`, `Tutorial/09_multi_part.py`, `Tutorial/10_multi_tempo.py`, `Tutorial/11_record_on_clock.py`, `Assorted/double_score.py`, `Assorted/guitar_arpeggios.py`, `Assorted/metric_phase.py`, `Assorted/octava.py`, `Assorted/record_and_export_midi.py`, `Assorted/scamp_to_max/polyphonic/`, `Compositions/reich_piano_phase.py`
- **tempo** — `Tutorial/02_tempo_change.py`, `Tutorial/10_multi_tempo.py`, `Assorted/evolving_form/`, `Assorted/metric_phase.py`, `Assorted/save_and_load_performance/`

### pitch

- **glissando** — `Tutorial/14_gliss_from_envelope.py`, `Tutorial/15_envelope_shorthand.py`, `Assorted/record_and_export_midi.py`
- **microtonal** — `Tutorial/18_microtonal.py`, `Assorted/record_and_export_midi.py`, `ScampExtensions/scale_example/`
- **scales** — `Assorted/conway.py`, `Assorted/voice_leading.py`, `ScampExtensions/scale_example/`
- **spelling** — `Tutorial/21_pitch_spelling.py`, `Assorted/post_processing.py`, `Assorted/voice_leading.py`

### envelopes

`Tutorial/12_envelopes_basic.py`, `Tutorial/13_envelopes_advanced.py`, `Tutorial/14_gliss_from_envelope.py`, `Tutorial/15_envelope_shorthand.py`, `Tutorial/17_volume_envelope.py`, `Assorted/evolving_form/`, `ScampExtensions/time_varying_parameter_example.py`

### notation

- **engraving** — `Tutorial/05_notation.py`, `Tutorial/06_time_signature.py`, `Tutorial/18_microtonal.py`, `Tutorial/24_osc_to_supercollider/`, `Assorted/chords_example.py`, `Assorted/voices.py`, `Assorted/voices_with_ottava.py`
- **output** — `Tutorial/05_notation.py`, `Assorted/double_score.py`, `Assorted/key_sig.py`, `Assorted/keyboard_input_with_notation.py`, `Assorted/record_and_export_midi.py`, `Assorted/run_as_server_render_scores.py`
- **properties** — `Tutorial/20_note_properties.py`, `Tutorial/21_pitch_spelling.py`, `Tutorial/22_staff_text.py`, `Tutorial/23_special_notations.py`, `Assorted/chords_example.py`, `Assorted/voices.py`, `Assorted/voices_with_ottava.py`
- **quantization** — `Tutorial/07_random_quantized.py`, `Tutorial/08_simplified_quantization.py`, `Assorted/quantization.py`, `Compositions/reich_piano_phase.py`
- **spanners** — `Tutorial/29_spanners.py`, `Assorted/octava.py`, `Assorted/post_processing.py`, `Assorted/voices_with_ottava.py`

### playback

- **adjustments** — `Tutorial/20_note_properties.py`, `Tutorial/23_special_notations.py`
- **external** — `Tutorial/19_playback_implementations.py`, `Tutorial/24_osc_to_supercollider/`, `Tutorial/25_MIDI_in_out.py`, `Assorted/evolving_form/`, `Assorted/midi_keyboard_mapper.py`, `Assorted/osc_playback/`, `Assorted/scamp_to_max/monophonic/`, `Assorted/scamp_to_max/polyphonic/`, `Compositions/evanstein_barlicity.py`, `Compositions/evanstein_lunar_trajectories.py`, `Compositions/leaf_loops.py`
- **handles** — `Tutorial/16_start_and_end_note.py`, `Assorted/chords_example.py`
- **implementations** — `Tutorial/19_playback_implementations.py`, `ScampExtensions/multipreset_example.py`
- **parameters** — `Assorted/osc_playback/`, `Assorted/record_and_export_midi.py`, `Assorted/scamp_to_max/monophonic/`, `Assorted/scamp_to_max/polyphonic/`

### interactive

- **gui** — `Assorted/qt_interactive.py`, `Assorted/run_as_server_render_scores.py`
- **input** — `Tutorial/25_MIDI_in_out.py`, `Tutorial/26_keyboard_input.py`, `Tutorial/27_mouse_input.py`, `Tutorial/28_osc_listening/`, `Assorted/keyboard_input_with_notation.py`, `Assorted/midi_keyboard_mapper.py`, `Assorted/qt_interactive.py`, `ScampExtensions/indispensibility_example.py`, `ScampExtensions/key_plane_example.py`, `Compositions/evanstein_lunar_trajectories.py`

### composition

- **algorithmic** — `Assorted/conway.py`, `Assorted/evolving_form/`, `ScampExtensions/indispensibility_example.py`, `ScampExtensions/l_system_example.py`, `Compositions/evanstein_barlicity.py`, `Compositions/leaf_loops.py`, `Compositions/reich_piano_phase.py`
- **form** — `Assorted/evolving_form/`, `ScampExtensions/time_varying_parameter_example.py`, `Compositions/leaf_loops.py`

### scamp_extensions

`Assorted/voice_leading.py`, `ScampExtensions/indispensibility_example.py`, `ScampExtensions/key_plane_example.py`, `ScampExtensions/l_system_example.py`, `ScampExtensions/multipreset_example.py`, `ScampExtensions/scale_example/`, `ScampExtensions/time_varying_parameter_example.py`, `Compositions/evanstein_barlicity.py`

### save and load

`Assorted/save_and_load_performance/`

### visualization

`Assorted/conway.py`, `Compositions/evanstein_barlicity.py`, `Compositions/leaf_loops.py`


## `Tutorial/`

A curated, teaching set introducing the key features of SCAMP.

- **`Tutorial/01_hello_world.py`** — Plays a C major arpeggio.
  <br>*tags:* basics — *API:* `Session`, `new_part`, `play_note`
- **`Tutorial/02_tempo_change.py`** — Same as Hello World example, but at half-tempo.
  <br>*tags:* time/tempo, basics — *API:* `Session`, `new_part`, `play_note`
- **`Tutorial/03_blocking_false.py`** — Demonstrating the ability to have non-blocking calls to play_note. This plays two notes that each last for two beats, but overlapping by one beat.
  <br>*tags:* time/clocks — *API:* `Session`, `new_part`, `play_note`, `wait`
- **`Tutorial/04_random_durations_and_rests.py`** — Loops a C major arpeggio twice, but with random, floating-point durations. Also sometimes adds a rest of up to a second between notes.
  <br>*tags:* basics — *API:* `Session`, `new_part`, `play_note`, `wait`
- **`Tutorial/05_notation.py`** — Plays a simple C Major arpeggio, and generates notation for it.
  <br>*tags:* notation/output, notation/engraving — *API:* `Performance`, `Score`, `Session`, `new_part`, `play_note`, `print_lilypond`, `start_transcribing`, `to_score`
- **`Tutorial/06_time_signature.py`** — Plays a simple C Major arpeggio, and generates notation for it in three different ways: - with a 3/8 time signature - with a 3/8 time signature for the first measure followed by 2/4 - with alternating 3/8 and 2/4 time signatures - with a list of bar lengths determining time signatures
  <br>*tags:* notation/engraving — *API:* `Score`, `Session`, `new_part`, `play_note`, `start_transcribing`, `to_score`
- **`Tutorial/07_random_quantized.py`** — Similar to the "Random Durations and Rests" example, except that now we generate notation. Since the lengths are floating point, quantization occurs in the call to "to_score"
  <br>*tags:* notation/quantization — *API:* `Session`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait`
- **`Tutorial/08_simplified_quantization.py`** — Same as last example except that we see two different levers for simplifying the notation: `max_divisor` (which defaults to 8) sets a hard cap on how finely we can divide the beat. `simplicity_preference` (which defaults to 2), rather than setting a hard cap, amplifies the error calculation for complicated divisors, leading to simpler beat divisions unless the complicated division is a very good match.
  <br>*tags:* notation/quantization — *API:* `Session`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait`
- **`Tutorial/09_multi_part.py`** — Plays two coordinated but independent parallel parts, one for oboe and one for bassoon.
  <br>*tags:* time/clocks — *API:* `Session`, `fork`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait_for_children_to_finish`
- **`Tutorial/10_multi_tempo.py`** — The trombone part plays quarter notes at the overall tempo of the session, which gradually accelerates from the default starting tempo of 60 BPM to 100 BPM. Meanwhile, the trumpet part plays eighth notes and runs in a child process that initially runs at the same speed as its parent (it inherits the parent's acceleration), but then slows down to half speed within the accelerating parent process.
  <br>*tags:* time/clocks, time/tempo — *API:* `MetricPhaseTarget`, `Moment`, `Session`, `current_clock`, `fork`, `new_part`, `play_note`, `set_rate_target`, `set_tempo_target`, `start_transcribing`, `to_score`
- **`Tutorial/11_record_on_clock.py`** — Same as previous example, except that the performance is recorded from the point of view of the trumpet part, resulting in the same sound notated in reference to a different changing tempo curve.
  <br>*tags:* time/clocks — *API:* `Clock`, `MetricPhaseTarget`, `Moment`, `Session`, `current_clock`, `fork`, `new_part`, `play_note`, `set_rate_target`, `set_tempo_target`, `start_transcribing`, `to_score`
- **`Tutorial/12_envelopes_basic.py`** — Create and plot two simple envelopes, one with evenly-spaced linear segments, and one with uneven, curved segments.
  <br>*tags:* envelopes — *API:* `Envelope`, `from_levels`, `show_plot`
- **`Tutorial/13_envelopes_advanced.py`** — A more comprehensive list of ways to construct and modify Envelopes.
  <br>*tags:* envelopes — *API:* `Envelope`, `adsr`, `append_envelope`, `ar`, `asr`, `from_function`, `from_levels`, `from_levels_and_durations`, `from_list`, `from_points`, `prepend_envelope`, `release`, `...`
- **`Tutorial/14_gliss_from_envelope.py`** — Plays a glissando by passing an Envelope to the pitch parameter of play_note.
  <br>*tags:* pitch/glissando, envelopes — *API:* `Envelope`, `Session`, `new_part`, `play_note`, `start_transcribing`, `to_score`
- **`Tutorial/15_envelope_shorthand.py`** — Plays two glissandi by passing lists instead of envelopes to the pitch argument of play_note.
  <br>*tags:* pitch/glissando, envelopes — *API:* `Envelope`, `Session`, `new_part`, `play_note`, `start_transcribing`, `to_score`
- **`Tutorial/16_start_and_end_note.py`** — Plays notes by calling start_note (or start_chord) and then manipulating them afterward, instead of defining the course of the note from the beginning with "play_note". The "start_note" and "start_chord" functions return handles that can be used to change the pitch, volume or other parameters of the note after they have started, as well as end the note.
  <br>*tags:* playback/handles — *API:* `Session`, `change_pitch`, `change_volume`, `end`, `new_part`, `start_chord`, `start_note`, `start_transcribing`, `to_score`, `wait`
- **`Tutorial/17_volume_envelope.py`** — Plots an envelope representing a forte-piano-crescendo dynamic, and then uses it to affect the dynamics of a note's playback. This example shows that an Envelope can be passed to the volume argument of "play_note", just like it can to the pitch argument. (The list short-hand also works, by the way.)
  <br>*tags:* envelopes — *API:* `Envelope`, `Session`, `new_part`, `play_note`, `show_plot`
- **`Tutorial/18_microtonal.py`** — Plays a few microtonal chords and notates them, turning on exact microtonal annotations.
  <br>*tags:* pitch/microtonal, notation/engraving — *API:* `Session`, `new_part`, `play_chord`, `start_transcribing`, `to_score`
- **`Tutorial/19_playback_implementations.py`** — Shows how to create parts that use different implementations for playback. This assumes that you are connecting to a midi device on port zero.
  <br>*tags:* playback/implementations, playback/external — *API:* `MIDIStreamPlaybackImplementation`, `OSCPlaybackImplementation`, `PlaybackImplementation`, `Session`, `SoundfontPlaybackImplementation`, `add_osc_playback`, `add_streaming_midi_playback`, `new_midi_part`, `new_osc_part`, `new_part`, `new_silent_part`, `play_note`, `...`
- **`Tutorial/20_note_properties.py`** — Shows how the fourth (optional) properties argument to "play_note" can be used to affect other aspects of playback and notation, such as articulation and noteheads. All properties are ultimately converted into a NotePropertiesDictionary; If a string is given, it is parsed into key / value pairs. In many cases, e.g. with "staccato" below, SCAMP can infer that it is referring to an articulation.
  <br>*tags:* notation/properties, playback/adjustments — *API:* `Envelope`, `NotePlaybackAdjustment`, `NoteProperties`, `Session`, `beat`, `new_part`, `play_chord`, `play_note`, `start_transcribing`, `to_score`
- **`Tutorial/21_pitch_spelling.py`** — Demonstrates the ability to define note pitch spelling using the optional properties argument to "play_note". This can be done by explicitly setting it, or by defining the key in which it resides.
  <br>*tags:* pitch/spelling, notation/properties — *API:* `Session`, `new_part`, `play_chord`, `play_note`, `start_transcribing`, `to_score`
- **`Tutorial/22_staff_text.py`** — Demonstrates various ways of adding text annotations to notes that are played. Text is one of the various notational details that can be passed to the fourth, optional "properties" argument of play_note.
  <br>*tags:* notation/properties — *API:* `Session`, `Staff`, `StaffText`, `new_part`, `play_chord`, `play_note`, `start_transcribing`, `to_score`
- **`Tutorial/23_special_notations.py`** — Ornaments, tremolo and other single-note notations. These notational details are passed to the fourth, optional "properties" argument of play_note.
  <br>*tags:* notation/properties, playback/adjustments — *API:* `Envelope`, `NotePlaybackAdjustment`, `Session`, `new_part`, `play_chord`, `play_note`, `start_transcribing`, `to_score`
- **`Tutorial/24_osc_to_supercollider/`** — Playing back notes by sending OSC messages to the SuperCollider, which receives them and spawns Synths in response. Start SuperCollider and run the code blocks in `receive_from_supercollider.scd`, then run `osc_to_supercollider.py`. Note that the easy way to receive note events from SCAMP in SuperCollider specifically is with the ScampUtils quark, as demonstrated by `receive_from_supercollider_scamputils.scd`.
  <br>*tags:* playback/external, notation/engraving — *API:* `Envelope`, `Session`, `ar`, `new_osc_part`, `num_notes_playing`, `play_note`, `start_transcribing`, `to_score`, `wait`
- **`Tutorial/25_MIDI_in_out.py`** — Demonstration of receiving and sending live midi input to and from a midi keyboard. Every note received by the keyboard is immediately sent back to the keyboard a perfect fifth higher.
  <br>*tags:* playback/external, interactive/input — *API:* `Session`, `end`, `new_midi_part`, `print_available_midi_output_devices`, `register_midi_listener`, `start_note`, `wait_forever`
- **`Tutorial/26_keyboard_input.py`** — (WARNING: consumes key events and makes the keyboard otherwise unresponsive. To avoid this, you can remove the suppress=True flag under register_keyboard_listener) Demonstration of receiving computer keyboard events and using them to play notes based on the key number. Any key whose number code lies within a reasonable range triggers the playback of a note of that MIDI pitch.
  <br>*tags:* interactive/input — *API:* `Session`, `end`, `new_part`, `register_keyboard_listener`, `start_note`, `wait_forever`
- **`Tutorial/27_mouse_input.py`** — (WARNING: consumes mouse events and makes the mouse otherwise unresponsive. To avoid this, you can remove the suppress=True flag under register_mouse_listener) Demonstration of receiving computer mouse events and using them to play notes based on x and y position. Notes are started on mouse down and released on mouse up.  Left click plays a piano note, and right click plays a flute note. X position controls pitch, Y controls volume. By moving the mouse after clicking, the pitch can be bent up and down and the volume can be changed.
  <br>*tags:* interactive/input — *API:* `Session`, `change_pitch`, `change_volume`, `end`, `new_part`, `register_mouse_listener`, `start_note`, `wait_forever`
- **`Tutorial/28_osc_listening/`** — Run `osc_listener.py` first, which uses Session.register_osc_listener to listen for OSC messages and play back notes and horrific bagpipe clusters. Then run `osc_sender.py` which simulates an external program sending OSC messages to to the listener script, leading to the aforementioned notes and horrific bagpipe clusters.
  <br>*tags:* interactive/input — *API:* `Session`, `new_part`, `play_chord`, `play_note`, `register_osc_listener`, `split`, `wait_forever`
- **`Tutorial/29_spanners.py`** — Demonstration of starting and stopping various spanners, such as slurs, hairpins, trills, brackets, and pedal lines. Note that there is some finickiness with both lilypond and MusicXML output. LilyPond does not allow multiple of the same spanner at the same time (at least in the same voice), whereas MusicXML does. If exporting to MusicXML, you can keep the spanners straight by providing a label. On the other hand, implementations of MusicXML in many notation programs mangle spanner input. So there's that.
  <br>*tags:* notation/spanners — *API:* `Session`, `StartSlur`, `StopSlur`, `fork`, `new_part`, `play_chord`, `play_note`, `start_transcribing`, `time`, `to_score`

## `Assorted/`

A grab bag of scripts showing idiomatic patterns, and methods of connecting SCAMP with other frameworks and software (MIDI input/output, PyQt, Max, SuperCollider).

- **`Assorted/chords_example.py`** — Chords with per-note noteheads, and a start_chord handle whose pitches change over time.
  <br>*tags:* notation/properties, notation/engraving, playback/handles — *API:* `Session`, `change_pitch`, `end`, `new_part`, `play_chord`, `start_chord`, `start_transcribing`, `to_score`, `wait`
- **`Assorted/conway.py`** — Conway's Game of Life sonified, with a pygame window used for visualization instead of matplotlib. Original by Raphael Radna; visualization ported to pygame.
  <br>*tags:* composition/algorithmic, pitch/scales, visualization — *API:* `Clock`, `Session`, `end`, `new_part`, `start_note`
- **`Assorted/double_score.py`** — Records two performances, turns them into scores, renders to abjad, and sticks them together!
  <br>*tags:* notation/output, time/clocks — *API:* `Score`, `Session`, `fork`, `new_part`, `play_note`, `start_transcribing`, `to_abjad`, `to_score`, `wait_for_children_to_finish`
- **`Assorted/evolving_form/`** — A piece for cello, pianoteq (MIDI), and SuperCollider (OSC), shaped by envelope-driven formal parameters. See definitions.py and formal_parameters.py.
  <br>*tags:* playback/external, envelopes, composition/algorithmic, time/tempo, composition/form — *API:* `Envelope`, `Moment`, `Session`, `fork`, `from_levels`, `kill`, `new_midi_part`, `new_osc_part`, `new_part`, `play_chord`, `play_note`, `set_rate_target`, `...`
- **`Assorted/guitar_arpeggios.py`** — Fingerpicking-style guitar arpeggios built from overlapping held notes.
  <br>*tags:* time/clocks — *API:* `Session`, `new_part`, `play_note`, `wait`
- **`Assorted/key_sig.py`** — Adds a key signature by exporting through pymusicxml and setting it on the first measure.
  <br>*tags:* notation/output — *API:* `Session`, `new_part`, `play_note`, `start_transcribing`, `to_music_xml`, `to_score`
- **`Assorted/keyboard_input_with_notation.py`** — (WARNING: consumes key events and makes the keyboard otherwise unresponsive. To avoid this, you can remove the suppress=True flag under register_keyboard_listener) Demonstration of receiving computer keyboard events and using them to play notes based on the key number. Any key whose number code lies within a reasonable range triggers the playback of a note of that MIDI pitch. Escape
  <br>*tags:* interactive/input, notation/output — *API:* `Session`, `end`, `fork`, `kill`, `new_part`, `play_note`, `register_keyboard_listener`, `start_note`, `start_transcribing`, `to_score`, `wait_forever`
- **`Assorted/metric_phase.py`** — Rate targets aligned to metric phase, so accelerations and decelerations land on downbeats.
  <br>*tags:* time/tempo, time/clocks — *API:* `MetricPhaseTarget`, `Moment`, `Session`, `current_clock`, `fork`, `new_part`, `play_note`, `set_rate_target`, `set_rate_targets`, `wait_for_children_to_finish`
- **`Assorted/midi_keyboard_mapper.py`** — A script written at the request of Paul Timmermans, in which different pitches or ranges of pitches on the keyboard can be mapped to particular instruments and chords. The heart of the script is the dictionary `pitch_to_instrument_and_pitches`, which expresses, for each key, which pitches and on which instrument should be played.
  <br>*tags:* playback/external, interactive/input — *API:* `Session`, `end`, `new_midi_part`, `new_part`, `print_available_midi_input_devices`, `print_available_midi_output_devices`, `register_midi_listener`, `split`, `start_chord`, `start_note`, `wait_forever`
- **`Assorted/octava.py`** — A short passage of random notes for violin and piano, which uses the optional note properties argument to `play_note` to apply ottava when notes are very high or very low.
  <br>*tags:* notation/spanners, time/clocks — *API:* `Session`, `fork`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait`, `wait_for_children_to_finish`
- **`Assorted/osc_playback/`** — Uses a new_osc_part to send messages to a running SuperCollider script at OSCListenerPython.scd. To test out, run all the code blocks in OSCListenerPython.scd, make sure that the port below matches the result of NetAddr.langPort, and then run this script.
  <br>*tags:* playback/external, playback/parameters — *API:* `Session`, `fork`, `new_osc_part`, `play_note`, `wait`, `wait_forever`
- **`Assorted/post_processing.py`** — Post-processes a recorded Performance of a random walk of thirds and fifths, so that every time three consecutive notes are a triad, they are slurred together and spelled consistently.
  <br>*tags:* notation/spanners, pitch/spelling — *API:* `Performance`, `Session`, `SpellingPolicy`, `StartSlur`, `StopSlur`, `get_note_iterator`, `new_part`, `play_note`, `start_transcribing`, `to_score`
- **`Assorted/qt_interactive.py`** — A draggable PyQt rectangle drives live playback in a server session. Moving the rectangle fires a callback that sets the tempo of the clock running the note loop; its vertical position still sets the pitch.
  <br>*tags:* interactive/gui, interactive/input — *API:* `Envelope`, `Session`, `fork`, `new_part`, `play_note`, `run_as_server`, `start_transcribing`, `to_score`, `value_at`
- **`Assorted/quantization.py`** — Records a loose piano improvisation against a metronome, then plays back the quantized version.
  <br>*tags:* notation/quantization — *API:* `MeasureQuantizationScheme`, `QuantizationScheme`, `Session`, `fork`, `new_part`, `play`, `play_chord`, `play_note`, `quantized`, `start_transcribing`, `wait`
- **`Assorted/record_and_export_midi.py`** — Records glissandi with microtonal pitches and playback params (fast-forwarded), then exports the performance as a MIDI file.
  <br>*tags:* time/clocks, pitch/glissando, pitch/microtonal, playback/parameters, notation/output — *API:* `Envelope`, `Moment`, `Session`, `export_to_midi_file`, `fast_forward`, `fork`, `kill`, `new_part`, `play_note`, `set_rate_target`, `start_transcribing`
- **`Assorted/run_as_server_render_scores.py`** — Runs the session as a server, repeatedly recording short fragments and popping up a score for each.
  <br>*tags:* interactive/gui, notation/output — *API:* `Score`, `Session`, `fork`, `new_part`, `play_note`, `run_as_server`, `start_transcribing`, `to_score`
- **`Assorted/save_and_load_performance/`** — Contains two scripts: One that plays some music and records a portion of that music to a JSON file, and a second that reads the JSON file and plays the recorded performance repeatedly while accelerating.
  <br>*tags:* save and load, time/tempo — *API:* `Ensemble`, `Envelope`, `Moment`, `Performance`, `Session`, `fork`, `get_beat`, `new_part`, `play`, `play_note`, `set_tempo_target`, `start_transcribing`, `...`
- **`Assorted/scamp_to_max/monophonic/`** — Sends monophonic notes with an extra playback parameter over OSC to Max. See the accompanying Max patch, which shows how to receive and route those messages.
  <br>*tags:* playback/external, playback/parameters — *API:* `Session`, `new_osc_part`, `play_note`, `wait`
- **`Assorted/scamp_to_max/polyphonic/`** — Sends overlapping glissando notes over OSC to Max. See the accompanying Max patch, which receives and routes those messages using a poly object.
  <br>*tags:* playback/external, time/clocks, playback/parameters — *API:* `Session`, `new_osc_part`, `play_note`, `wait`
- **`Assorted/voice_leading.py`** — Rule-based four-part voice leading over a scale, spelled in E major.
  <br>*tags:* pitch/spelling, pitch/scales, scamp_extensions — *API:* `Session`, `Voice`, `new_part`, `play_chord`, `play_note`, `start_transcribing`, `to_score`
- **`Assorted/voices.py`** — Demonstration of how to place notes in specific voices within a staff/part. Named voices keep notes together in the same voice, and numbered voices determine exactly which voice they go in. By default SCAMP allows up to four voices per staff, but this can easily become quite messy. Set `engraving_settings.max_voices_per_staff` to limit the number of voices per staff, placing overflow voices on separate staves.
  <br>*tags:* notation/properties, notation/engraving — *API:* `Session`, `fork`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait`, `wait_for_children_to_finish`
- **`Assorted/voices_with_ottava.py`** — Same as the voices example, but with ottava applied to certain voices. These ottava contradict one another when the voices are (by default) placed on the same staff, so the largest octave line wins and a warning is emitted. To avoid this conflict, set `engraving_settings.max_voices_per_staff = 1` to place each voice in a separate staff.
  <br>*tags:* notation/properties, notation/engraving, notation/spanners — *API:* `Session`, `fork`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait`, `wait_for_children_to_finish`

## `ScampExtensions/`

Examples exercising the optional `scamp_extensions` package (scales, playback utilities, algorithmic power tools).

- **`ScampExtensions/indispensibility_example.py`** — Mouse position controls a rhythmic texture based on Barlow's beat indispensability (barlicity extension).
  <br>*tags:* interactive/input, composition/algorithmic, scamp_extensions — *API:* `Session`, `change_pitch`, `end`, `new_part`, `play_note`, `register_mouse_listener`, `start_note`, `wait`
- **`ScampExtensions/key_plane_example.py`** — Maps the computer keyboard onto a 2D grid of pitches with scamp_extensions' KeyPlane; each key press starts a flute note whose pitch and volume come from its row and column.
  <br>*tags:* interactive/input, scamp_extensions — *API:* `Session`, `end`, `new_part`, `start_note`
- **`ScampExtensions/l_system_example.py`** — Example usage of the from :class:`~scamp_extensions.process.l_system.LSystem` class, which allows you to set a vocabulary of symbols, set their rewrite rules and meanings, and evolve and play the resulting L-System.
  <br>*tags:* composition/algorithmic, scamp_extensions — *API:* `Session`, `fork`, `new_part`, `play_note`, `wait`, `wait_for_children_to_finish`
- **`ScampExtensions/multipreset_example.py`** — Demo of the MultiPresetInstrument, a convenience meta-instrument for subsuming several different playing techniques and their associated notations under a single instrument interface.
  <br>*tags:* playback/implementations, scamp_extensions — *API:* `ScampInstrument`, `Session`, `change_pitch`, `end`, `play_note`, `start_note`, `start_transcribing`, `to_score`, `wait`
- **`ScampExtensions/scale_example/`** — Demo of the scamp_extensions Scale object, a highly flexible representation of a scale that can be indexed into infinitely in both directions from a root note. Scales can be microtonal (and even loaded from a scala file), and are constructed from intervals that can be expressed as either a frequency ratio, a distance in cents, or a combination of the two. Scales can also be transposed and modally rotated.
  <br>*tags:* scamp_extensions, pitch/scales, pitch/microtonal — *API:* `Session`, `new_part`, `play_chord`, `play_note`
- **`ScampExtensions/time_varying_parameter_example.py`** — A script using the context-sensitive :class:`~expenvelope.envelope.Envelope` wrapper :class:`TimeVaryingParameter`, which reads into the underlying envelope at the current clock's beat or time when called.
  <br>*tags:* scamp_extensions, envelopes, composition/form — *API:* `Envelope`, `Session`, `current_clock`, `fork`, `from_levels`, `new_part`, `play_note`, `wait_for_children_to_finish`

## `Compositions/`

Full pieces and reconstructions of existing works.

- **`Compositions/evanstein_barlicity.py`** — A large interactive piece built on harmonicity and indispensability (barlicity extension), with multidimensional-scaling visualization in Qt. This was the initial script for the piece, which ultimately became the notated work for piano and electronics that you can view here: https://www.youtube.com/watch?v=xMpET9KKOrw
  <br>*tags:* composition/algorithmic, scamp_extensions, visualization, playback/external — *API:* `Envelope`, `Session`, `fork`, `get_beat`, `get_time`, `kill`, `new_part`, `play_chord`, `play_note`, `run_as_server`, `send_midi_cc`, `start_transcribing`, `...`
- **`Compositions/evanstein_lunar_trajectories.py`** — Interactive piano script for the first movement of "Lunar Trajectories". The `notes` list below is a list of all the notes played by the middle arpeggio part in the first movement of the Moonlight Sonata, in order. If a pitch is in that list, then when it is depressed, the piano reacts by playing whichever pitches follow that pitch the first time it occurs in the list. If a pitch is not in the list, then instead we look for the same pitch class but in a different octave, and follow it up by the notes that follow that pitch (transposed back up or down by however many octaves). Every pitch class appears in the first movement, so we don't have the issue of searching for a pitch class that doesn't occur.
  <br>*tags:* playback/external, interactive/input — *API:* `Session`, `current_clock`, `fork`, `new_midi_part`, `play_note`, `print_available_midi_input_devices`, `print_available_midi_output_devices`, `register_midi_listener`, `send_midi_cc`, `wait`, `wait_forever`
- **`Compositions/leaf_loops.py`** — Generative process behind Marc Evanstein's "Leaf Loops" for violin and viola. The shapes, note attack points, and worm shape for several different leaves are found in the LeafPoints directory.
  <br>*tags:* playback/external, composition/algorithmic, composition/form, visualization — *API:* `Clock`, `Session`, `end_all_notes`, `get_time`, `new_midi_part`, `new_part`, `play_note`, `run_as_server`, `start_note`
- **`Compositions/reich_piano_phase.py`** — Steve Reich's Piano Phase: the same figure forked at 100 vs. 98 BPM, transcribed on one clock.
  <br>*tags:* time/clocks, notation/quantization, composition/algorithmic — *API:* `QuantizationScheme`, `Session`, `fork`, `new_part`, `play_note`, `start_transcribing`, `to_score`, `wait`

## `JunkDrawer/`

Uncurated scratch scripts, kept for reference only. Not indexed by feature.

- **`JunkDrawer/NotationVSPerformance.py`** — A silent part records clean notation while the audible part plays the same music with wonky timing; both transcriptions are exported.
  <br>*tags:* silent part, transcription, midi export
- **`JunkDrawer/OldTutorialExamples/articulations.py`** — Articulations (staccato, accent, tenuto, ...) via the properties argument.
  <br>*tags:* articulations, note properties, notation
- **`JunkDrawer/OldTutorialExamples/hello_world.py`** — A C major scale, transcribed and shown as notation.
  <br>*tags:* play_note, basics, notation
- **`JunkDrawer/OldTutorialExamples/multipleTempos.py`** — Three wind parts on independent looping and functional tempo envelopes.
  <br>*tags:* polytempo, tempo function, fork
- **`JunkDrawer/OldTutorialExamples/note_spelling.py`** — Ways to control pitch spelling: session/instrument defaults, keys, and per-note settings.
  <br>*tags:* pitch spelling, note properties
- **`JunkDrawer/bananaphone.py`** — Three-part texture (two violins and a "bass banjo") accelerating from tempo 60 to 300.
  <br>*tags:* fork, tempo change, glissando, overlapping notes, engraving settings
- **`JunkDrawer/bunchStuff.py`** — Grab-bag scratch script: OSC sine-wave glissandi plus microtonal staccato piano.
- **`JunkDrawer/fifteen_sixteen.py`** — Quantizes a rhythm against 15/16 and other changing time signatures.
  <br>*tags:* quantization, quantization settings, time signatures, fast-forward
- **`JunkDrawer/glissTest2.py`** — Scratch test of glissando engraving with grace-note control points.
- **`JunkDrawer/glissando_test.py`** — Random glissandi and chord glissandi, quantized, saved to JSON, then reloaded and replayed.
  <br>*tags:* glissando, quantization, quantization settings, save and load
- **`JunkDrawer/karlclock.py`** — Scratch test: two forked processes playing chords and fast notes.
- **`JunkDrawer/karlclock_interactive.py`** — Scratch test: number keys change the tempo of forked processes (via pynput).
- **`JunkDrawer/key_clocks.py`** — Child and grandchild clocks with a sinusoidal tempo function and rate flipping.
  <br>*tags:* nested clocks, tempo function, fork
- **`JunkDrawer/midi_channel_manager.py`** — Scratch test of the internal MIDIChannelManager channel-assignment logic.
- **`JunkDrawer/random_walk_fragments.py`** — Forks overlapping random-walk melodies into a single instrument, then renders the same performance at several max_voices_per_staff settings to compare how the fragments get distributed across voices and staves.
  <br>*tags:* fork, random walk, quantization, max_voices_per_staff
- **`JunkDrawer/repeated_notes.py`** — Scratch test of rapid repeated notes across multiple MIDI channels.
- **`JunkDrawer/save_and_load_ensemble.py`** — Uses a bare Ensemble for playback (no musical time), with commented-out save/load to JSON.
  <br>*tags:* ensemble, save and load
- **`JunkDrawer/tempo_test.py`** — Scratch test of chained tempo targets and bar-line placement options.
- **`JunkDrawer/ticker_test.py`** — Scratch test of clockblocks tempo changes made from a foreign thread.
- **`JunkDrawer/voice-leading_weird.py`** — Experimental variant of voice-leading.py with randomized bass motion.

## Non-Python companion files

SuperCollider scripts, Max patches, and saved data used by the examples above:

- `Assorted/evolving_form/Crackler.scd`
- `Assorted/osc_playback/OSCListenerPython.scd`
- `Assorted/save_and_load_performance/perfShakoboe.json`
- `Assorted/scamp_to_max/monophonic/MonoMain.maxpat`
- `Assorted/scamp_to_max/monophonic/MonoSynth.maxpat`
- `Assorted/scamp_to_max/monophonic/scampreceive.maxpat`
- `Assorted/scamp_to_max/polyphonic/PolyMain.maxpat`
- `Assorted/scamp_to_max/polyphonic/PolySynth.maxpat`
- `Assorted/scamp_to_max/polyphonic/scampreceive.maxpat`
- `Compositions/LeafPoints/dwarfBirch.json`
- `Compositions/LeafPoints/dwarfBirchAttackPoints.json`
- `Compositions/LeafPoints/dwarfBirchWorm.json`
- `Compositions/LeafPoints/ivy.json`
- `Compositions/LeafPoints/ivyAttackPoints.json`
- `Compositions/LeafPoints/ivyWorm.json`
- `Compositions/LeafPoints/larkSpur.json`
- `Compositions/LeafPoints/larkSpurAttackPoints.json`
- `Compositions/LeafPoints/larkSpurWorm.json`
- `Tutorial/24_osc_to_supercollider/receive_from_supercollider.scd`
- `Tutorial/24_osc_to_supercollider/receive_from_supercollider_scamputils.scd`
