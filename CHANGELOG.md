# Changelog

> These changelogs are AI-written and human-reviewed, because no one (least of all my wife
> and kids) wants me wasting my precious time meticulously documenting this shit, useful
> though it may be.

All notable user-facing changes to SCAMP are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.10.0] - 2026-07-12

This release moves SCAMP onto **clockblocks 1.0**, which was redesigned around a single
central scheduler. Most SCAMP code is unaffected, but the clock-facing API changed in a
few places — see *Migrating* below, and the
[clockblocks 1.0 changelog](https://github.com/MarcTheSpark/clockblocks/blob/main/CHANGELOG.md)
for the full picture.

### Changed

- **Requires clockblocks 1.0**, and with it: forked functions no longer receive the clock
  as an argument, and tempo targets are expressed with a `Moment` (`after_beats(4)`,
  `at_time(30)`, …) rather than a bare duration.
- Note positions are transcribed via clockblocks' `TimeStamp`/`TimeStampInterval`, which
  makes them correct when notes are played from foreign threads — a note triggered by a
  MIDI, OSC, or keyboard callback is now recorded at the moment it actually sounded
  instead of at the previous scheduler event.
- Parameter animation (glissandi, dynamic envelopes, other continuous parameters) is
  driven by scheduled leaf actions rather than a background unsynchronized thread.
- Tolerant floating-point comparisons throughout the transcribe → quantize → score
  pipeline, and floating-point dust is snapped out of finished score notes. Some scores
  will quantize slightly differently — generally more correctly — than in 0.9.x.
- `Performance`'s repr now surfaces a non-default tempo.
- Settings renamed: `show_music_xml_command_line` → `music_xml_open_command`.
- Settings subclasses are now dataclasses, and "auto" settings resolve lazily.

### Added

- First-run experience polish: clearer soundfont/LilyPond discovery messages.
- An example demonstrating keyboard input recorded to notation against a metronome.

### Removed

- `fork_unsynchronized` (follows its removal from clockblocks). For detached background
  work that never calls `wait()`, use a plain `threading.Thread(..., daemon=True)`.
- Implicitly passed `clock` arguments; call `current_clock()` instead.

### Fixed

- Enharmonic spelling is stable against floating-point noise.
- The soundfont recording timer no longer depends on a code path that had been dead since
  parameter animation moved to scheduled actions.

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
s.set_tempo_target(120, after_beats(4))
```

## Earlier versions

For changes prior to 0.10.0, see the commit history.
