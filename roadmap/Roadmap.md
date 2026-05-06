# SCAMP Roadmap

Current planned work. Older roadmaps (1.0, 2.0) are in `archive/` — most items
there are either done, abandoned, or superseded; revisit only as reference.

## Summary

1. [Test infrastructure & settings refactor](#test-infrastructure--settings-refactor) — pytest + syrupy migration, targeted unit tests, dataclass-based settings with per-`Session` overrides.
2. ["auto"-style settings: a general approach](#auto-style-settings-a-general-approach) — design a reusable pattern for settings whose default is "figure it out on first use".
3. [Documentation: switch source links from sourcehut to GitHub](#documentation-switch-source-links-from-sourcehut-to-github) — audit and update canonical source URLs across docs, README, and package metadata.
4. [Documentation: refresh installation & dependency story](#documentation-refresh-installation--dependency-story) — installation is now simpler since wheels bundle FluidSynth; review other dependency notes for staleness.

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

6. **Move `_ScampSettings` from `SimpleNamespace` to `dataclass`, internally.**
   Public API unchanged. Get type hints, IDE completion, less migration
   ceremony.
7. **Stop auto-rewriting JSON on load.** Split "load + fill defaults in
   memory" (silent) from "migrate file on disk" (explicit, on version upgrade
   or via a CLI command).
8. **Let `Session` accept a settings override.** `Session(playback_settings=…,
   quantization_settings=…)`. Globals stay as the default for top-of-script
   ergonomics, but a Session can carry its own. Real test isolation; makes
   "what settings did this Performance use?" answerable.

## "auto"-style settings: a general approach

`default_audio_driver = "auto"` is currently a one-off: a sentinel string that
triggers a one-time probe (`auto_detect_audio_driver_if_needed`), which writes
the resolved value back into the persisted settings. The mechanism is fragile
— callers have to remember to invoke the resolver *before* reading the
setting (the dict-key bug in `SoundfontPlaybackImplementation` was caused by
reading `default_audio_driver` while it was still `"auto"`), and we now have
an awkward `"auto"` literal threading through the type as if it were a real
driver name.

Worth designing a general pattern for "settings whose default is 'figure it
out the first time'" — candidates besides audio driver: lilypond binary
location (already half-implemented as `_should_search_for_lilypond`), maybe
soundfont search paths. Possible shapes:

- A `Resolvable` setting type that lazily computes on first read and caches
  (so the resolver runs at the read site, not at scattered call sites).
- Or, resolve all such settings once at `import scamp` time / first
  `Session()` construction, with an opt-out for tests.
- Or keep the explicit-probe model but standardize: every setting with an
  `"auto"` value has a registered resolver, and a single
  `playback_settings.resolve_pending()` is called from one well-known place.

Tie this in with Phase C of the settings refactor (dataclass migration, load
vs. migrate split) — a cleaner settings substrate makes any of these easier.

## Documentation: switch source links from sourcehut to GitHub

The published docs still point to sourcehut as the canonical source. Audit and
update all references (docs site, README, package metadata, any
`project_urls` in `pyproject.toml`, in-code links) to point at GitHub.

## Documentation: refresh installation & dependency story

Installation is now substantially simpler than what the docs describe:
prebuilt wheels bundle FluidSynth (via `auditwheel`/`delocate-wheel`/Windows
DLL drop-in), so users no longer need to install FluidSynth separately on
most platforms. The install instructions, troubleshooting sections, and any
"prerequisites" lists should be rewritten to reflect this.

While in there, do a broader staleness pass:

- Other optional dependencies (`abjad`, `python-rtmidi`, `pynput`) — make sure
  the `pip install scamp[all]` story and per-feature notes are current.
- LilyPond / MusicXML export prerequisites.
- Python version requirements (now ≥ 3.12).
- Any references to old build/install workflows that predate the `src/`
  layout and cibuildwheel-based wheel pipeline.
- Screenshots, example output, and links that may have rotted.
