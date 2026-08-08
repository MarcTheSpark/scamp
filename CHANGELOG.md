# Changelog

> These changelogs are AI-written and human-reviewed, because no one (least of all my wife
> and kids) wants me wasting my precious time meticulously documenting this shit, useful
> though it may be.

All notable user-facing changes to SCAMP are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **`Performance.export_to_midi_file()` now applies playback adjustments**, so the exported MIDI reflects what
  would be *heard* — staccato shortening notes, accents/sfz raising velocity — rather than the bare notated
  values. Realtime playback already did this; MIDI export was the odd one out. Velocities are clamped to the
  valid MIDI range, so an adjustment pushing volume above 1.0 caps at 127 instead of corrupting the file.

### Fixed

- **A tuplet on a compound beat (e.g. the 1.5-quarter beat of a 5/8 or 3/8 measure) no longer crashes
  notation export** with `AssignabilityError` / "does not resolve to single note type". Affects both LilyPond 
  (abjad) and MusicXML output. Notes spanning several tuplet subdivisions on a compound beat now also tend 
  to notate as a single dotted note rather than tied notes.
- **Tempo and metronome marks in exported MusicXML now carry an explicit assignment to sit above the top 
  staff.** They previously carried no staff assignment, so some readers drifted a mark down toward a lower 
  staff of the system.
- **Setting an instrument's `default_spelling_policy` to a string (e.g. `"E major"`) now works.** Passing a
  string to `new_part(default_spelling_policy=...)`, or assigning one after the fact, previously stored the raw
  string instead of a `SpellingPolicy`, breaking spelling at transcription time; strings and alteration tuples
  are now interpreted the same way the `Ensemble`-level default already was.
- **Reloading a saved `Performance` that carried a non-trivial recorded tempo curve no longer plays back at
  the wrong tempo (or appears to hang).** The `TempoEnvelope` JSON round-trip was inverting the curve; relies
  on a matching fix in clockblocks. Note that saved-performance JSON now stores tempo-curve levels as tempo
  (bpm) rather than beat length — files written by older versions should be re-saved to migrate.
- **A blocking `play_note()` or `wait()` inside a keyboard/MIDI/OSC callback no longer hangs the session.**
  Instead, it raises `SchedulerHeldError` (re-exported from clockblocks), pointing you to fork the timed
  action so the callback returns immediately.
- **A recorded tempo curve now reaches the moment you call `stop_transcribing`**, even when the recorded
  clock is mid-wait or you stop from a different clock. Previously the extracted tempo envelope could end
  early — at the beat the recorded clock last woke at — dropping the final stretch of tempo; recorded notes
  past that point were left without a tempo curve.
- **Instantaneous tempo changes no longer render as tiny accelerandi/ritardandi** in a transcribed score
  (e.g. a looping stepwise `TempoEnvelope`). Relies on a matching fix in clockblocks.

## [0.12.0] - 2026-08-01

### Added

- `terminate_forked_children()` is re-exported from clockblocks — the counterpart to
  `wait_for_children_to_finish()` that ends a script's (or a forked part's) still-running forks where
  they are. Either one answers the new warning below.

### Changed

- **Requires clockblocks >= 1.2.** The cut-off behavior below relies on `kill()` there now finishing a
  clock's wind-down before it returns, so the cut lands at a deterministic beat. `terminate_forked_children` is
  also a clockblocks 1.2 addition.

- **A forked process (or script, or `with Session()` block) that ends with sub-forks still running now
  cuts them off and warns, naming the clock or note affected.** Call `wait_for_children_to_finish()` to let them
  play out, or `terminate_forked_children()` to end them deliberately (either silences the warning). Most
  visibly, a `play_note(..., blocking=False)` that outlasts the function that started it is now cut short
  instead of ringing on.

### Fixed

- **A note cut short by an ending clock is now consistently notated where it was actually cut off.** 
  Previously, the scheduler could move forward while the clock was winding down, leading to the transcriber
  sometimes reading the wrong beat. (The fix is implemented in clockblocks.)

- **A tempo that jumps instantaneously right at beat 0 no longer places two conflicting metronome marks at
  the same spot.**

## [0.11.0] - 2026-07-27

### Added

- Sustain pedal methods on `ScampInstrument`: `pedal_down(press_amount)`, `pedal_up()`, and
  `pedal_change(duration, press_amount)` send CC 64 to all midi-based playback implementations.
  `pedal_change` lifts and re-presses the pedal (re-press runs in a forked process, so the call
  returns immediately), defaulting to the press amount of the last `pedal_down`/`pedal_change`.

- `get_beat()` and `get_time()` are re-exported from clockblocks, joining `get_tempo()` /
  `get_rate()` / `get_beat_length()`. They read the position of the clock running on the calling
  thread, so `while get_beat() < 16:` no longer needs `current_clock().beat`. Inside a `fork`,
  they report that fork's position, not the Session's.

### Changed

- **Requires clockblocks >= 1.1 (and now caps at < 2):** the clock position accessors became
  read-only properties there, so write `s.beat`, `s.time`, `s.absolute_rate` etc. without
  parentheses. The old `s.beat()` spelling still works with a `DeprecationWarning` until
  clockblocks 2.0. All bundled examples use the new spelling.

## [0.10.0] - 2026-07-12

This release moves SCAMP onto **clockblocks 1.0**, which was redesigned around a single
central scheduler. Most SCAMP code is unaffected, but the clock-facing API changed in a
few places — see *Migrating* below, and the
[clockblocks 1.0 changelog](https://github.com/MarcTheSpark/clockblocks/blob/main/CHANGELOG.md)
for the full picture.

### Changed

- **Requires clockblocks 1.0**, and with it: forked functions no longer receive the clock
  as an argument, and tempo targets are expressed with a `Moment`
  (`Moment.after_beats(4)`, `Moment.at_time(30)`, …) rather than a bare duration.
- Note positions are transcribed via clockblocks' `TimeStamp`/`TimeStampInterval`. Notes
  played from foreign threads (a MIDI, OSC, or keyboard callback) were already stamped at
  the moment they actually sounded; this simply gets there through a clockblocks primitive
  rather than scamp's own bookkeeping.
- Parameter animation (glissandi, dynamic envelopes, other continuous parameters) is driven
  by scheduled leaf actions rather than a background unsynchronized thread.
- Tolerant floating-point comparisons throughout the transcribe → quantize → score pipeline,
  and floating-point dust is snapped out of finished score notes, so `Performance` and
  `Score` reprs show the durations and levels you actually asked for instead of their
  floating-point residue. Notated output is unchanged; what moves is numeric detail, plus a
  couple of sub-perceptible MIDI shifts (one tempo event by ~1ppm, six CC11 expression
  events from 126 to 127).
- `print_dependency_status()` — which reports, per optional dependency, whether the feature
  it powers is available — gains a **LilyPond** row alongside FluidSynth, sf2utils,
  python-osc, python-rtmidi, pynput, and abjad. Soundfont and LilyPond discovery messages
  are clearer on first run.
- `Performance`'s repr now surfaces a non-default tempo.
- Settings renamed: `show_music_xml_command_line` → `music_xml_open_command`.
- Settings subclasses are now dataclasses, and "auto" settings resolve lazily.

### Added

- An example demonstrating keyboard input recorded to notation against a metronome.

### Removed

- `fork_unsynchronized` (follows its removal from clockblocks). For detached background
  work that never calls `wait()`, use a plain `threading.Thread(..., daemon=True)`.
- Implicitly passed `clock` arguments; call `current_clock()` instead.

### Fixed

- Enharmonic spelling is stable against floating-point noise.
- The soundfont recording timer no longer depends on a code path that had been dead since
  parameter animation moved to scheduled actions.
- No longer starts a FluidSynth MIDI *input* driver when creating a synth. Nothing in SCAMP read from
  it, and on Windows machines with no MIDI input devices attached it printed alarming (but harmless)
  errors on startup: `not enough MIDI in devices found. Expected:1 found:0` and
  `Device "default" does not exists`. Playback was unaffected, but the messages made it look like
  SCAMP had failed.

### Migrating

```python
# 0.9.x
def melody(clock):
    ...
s.fork(melody)
s.set_tempo_target(120, 4)

# 0.10.0
def melody():
    clock = current_clock()   # only if you actually need it
    ...
s.fork(melody)
s.set_tempo_target(120, Moment.after_beats(4))
``` 

## Earlier versions

For changes prior to 0.10.0, see the commit history.
