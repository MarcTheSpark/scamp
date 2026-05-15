# SCAMP Roadmap

Current planned work. Older roadmaps (1.0, 2.0) are in `archive/` — most items
there are either done, abandoned, or superseded; revisit only as reference.

## Summary

1. [Test infrastructure & settings refactor](#test-infrastructure--settings-refactor) — pytest + syrupy migration, targeted unit tests, dataclass-based settings with per-`Session` overrides.
2. [Assorted Fixes](#assorted-fixes)

Recently completed (2026-05-06): sourcehut → GitHub link migration across all five packages, and a full refresh of the installation docs (FluidSynth bundling, Python ≥ 3.12, `scamp[all]` extras, abjad pin, Mac LilyPond instructions, dependency-status testing snippet).

## Test infrastructure & settings refactor

Replace the hand-rolled golden-output runner with pytest + syrupy, add targeted
unit tests for the algorithmic hotspots, and modernize the settings system.
Done in eight bite-sized steps so each one ships independently.

### Phase A — Test infrastructure (no behavior changes)

1. **Run existing tests under pytest, unchanged.** Add `pytest` as a dev dep,
   parametrize over the example `.py` files, keep `test_examples.py` working in
   parallel.
2. **Fix the determinism leak.** `get_example_result` resets
   `engraving_settings` but not `playback_settings` or `quantization_settings`.
   Reset all three.
3. **Replace hand-rolled `.json` snapshots with `syrupy`.** Migrate one example
   first to feel out the workflow, then bulk-convert. `--snapshot-update`
   replaces the `-s` flag.
4. **Retire the old `test_examples.py` script.** Delete it once syrupy +
   pytest cover everything. Update CLAUDE.md.

### Phase B — Targeted unit tests

5. **Pick 2–3 algorithmic hotspots and write real unit tests.** Candidates:
   tricky quantization cases, tuplet nesting, microtonal channel allocation.
   Build a small `Performance` by hand, call the function, assert. No clocks,
   no soundfonts.

### Phase C — Settings refactor

6. ~~**Move `_ScampSettings` from `SimpleNamespace` to `dataclass`, internally.**~~
   Done 2026-05-06/07. Each subclass is `@dataclass(repr=False, eq=False)`;
   field declarations are now the single source of truth for both schema and
   defaults (no more parallel `factory_defaults` dict and no more
   `self.x = self.y = ... = None` IDE-hint init lines). Auto-init handles
   construction (kwargs work and are IDE-completable); a separate
   `_from_dict` classmethod is the JSON-load entry point with migration.
7. **Stop auto-rewriting JSON on load.** Split "load + fill defaults in
   memory" (silent) from "migrate file on disk" (explicit, on version upgrade
   or via a CLI command).
8. **Let `Session` accept a settings override.** `Session(playback_settings=…,
   quantization_settings=…)`. Globals stay as the default for top-of-script
   ergonomics, but a Session can carry its own. Real test isolation; makes
   "what settings did this Performance use?" answerable.

## ~~"auto"-style settings: a general approach~~ — done 2026-05-07

Implemented as a class-level resolver registry on `_ScampSettings`. Each
subclass declares `_resolvers = {field_name: resolver_fn}` and optionally
`_persist_after_resolve = {field_name, ...}`. Resolvable fields use
`field(default_factory=lambda: None)` so no class attribute masks
`__getattr__`; `__post_init__` deletes None instance attrs to "arm" the lazy
mechanism. `__getattr__` runs the resolver once, caches the result, and
optionally calls `make_persistent()`. Hot-path reads pay zero overhead since
non-resolver fields are normal instance attributes.

Three settings now use it:

- `playback_settings.default_audio_driver` (persisted — probing is slow)
- `engraving_settings.lilypond_dir` (persisted — search is slow;
  `_invalidate_lilypond_dir_if_stale()` re-arms if the cached binary is gone)
- `engraving_settings.music_xml_open_command` (not persisted — platform
  lookup is microseconds and not persisting avoids stale platform values)

The legacy `"auto"` sentinel in old persisted JSON is translated to None on
load (in `_from_dict`) so existing user config files migrate transparently.


## Assorted Fixes

- ~~Start-up vibes: Make all the text on first run about searching for stuff green, to say: this is all normal.~~ Done 2026-05-11: `utilities.first_run_notice()` prints the lilypond search, audio-driver probe, and lilypond-template install messages in green when stderr is a TTY.
- ~~print_dependency_status() should try to run get_abjad() and see if it finds lilypond. We want to know the status and location of the lilypond binary.~~ Done 2026-05-11: added a `LilyPond` row that calls `get_abjad()` (triggering the lazy lilypond_dir resolver) and reports the binary path via `shutil.which`.
- Semaphore leakage warnings on Mac. This could be a much broader thing, a Thonny thing, or a clockblocks thing
- Audit explicit `clock=` kwargs on `play_note` / `play_chord` / `play_note_from_pitch` (`instruments.py`) and `PerformancePart.play` / `Performance.play` (`performance.py`). Originally added for flexibility, but the only legitimate caller for `blocking=True` is `current_clock()` — anything else means waiting on a clock from the wrong thread, which clockblocks 1.0 will reject with `WrongThreadError`. Consider removing the parameter entirely (or restricting it to `blocking=False` use only). Think about the run_as_server() case though?
