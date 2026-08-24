# SCAMP Roadmap

Current planned work, grouped by topic. Older roadmaps (1.0, 2.0) are in
`archive/` — most items there are either done, abandoned, or superseded; revisit
only as reference.

## Summary

- **[Notation & voices](#notation--voices)** — quantize overlapping voices
  independently; transcribe non-note events (pedaling, etc.); a small idea for
  tagging unspecified-voice notes by their forking clock.
- **[Playback](#playback)** — MPE so microtonal pitch bend survives on external
  synths.
- **[Tests & settings](#tests--settings)** — pytest + syrupy migration, targeted
  unit tests, per-`Session` settings.
- **[AI tutor & workspace home](#ai-tutor--workspace-home)** — mature the tutor
  and give it (and the workspace-level files) a real repo. This cluster is the
  near-term focus.
- **[Assorted fixes](#assorted-fixes)** — small standalone items.

## Notation & voices

### Separate overlapping voices before quantizing

Today the order is backwards. `_quantize_performance_part` (quantization.py) walks each
source voice and **quantizes the whole voice first**, then `_collapse_chords`, then
`_separate_into_non_overlapping_voices` splits it into monophonic streams. So overlapping
notes that end up in *different* notated voices influence one another's quantization, and
every stream split off a voice is forced onto **one shared `QuantizationRecord`** (all the
`base`, `base_2`, `base_3` overage voices point at the same record) — they never get their
own subdivision choices.

The fix: **separate into non-overlapping voices first, then quantize each independently.**
Each stream gets its own record, chosen for its own rhythm. This is cleaner and should
improve notation of self-overlapping voices.

Notes / open questions:
- Records are already stored **per voice** (`part.voice_quantization_records` is a dict
  keyed by voice name; each `QuantizationRecord` holds per-measure `quantized_measures`),
  so the storage already supports independent records — it's the *computation* order that's
  shared, not the schema.
- Separation is greedy-by-onset and would run on **raw** (pre-quantization) times, which is
  arguably more correct (true overlap, not quantized overlap).
- `_collapse_chords` currently sits between the two steps; decide where it lands (probably
  still before separation, so a true chord isn't torn into two voices).
- Voices sharing a staff still need compatible barlines; independent per-voice subdivision
  within a measure is fine (different tuplets per voice are legal), but confirm the
  `QuantizationScheme` measure/time-signature choices stay consistent across a part's voices.

### Transcribable non-note events

`ScampInstrument.send_midi_cc` (and the pedal methods built on it) go straight
to the playback implementations — the `Transcriber` never sees them, so pedaling
is lost from the resulting `Performance`/`Score`. Try to make these transcribed.

This is probably part of a larger redesign: `Performance` currently only holds
`PerformanceNote`s, so it needs a notion of events that aren't attached to
notes (cc/pedal messages, maybe program changes, tempo-independent markers).
Open questions: how such events survive quantization, and what they become at
the `Score` stage (e.g. pedal marks as spanners) vs. playback-only.

### Auto-tag unspecified-voice notes by forking clock

Low priority. Consider tagging notes left in the unspecified voice with their forking
clock's id (e.g. `_unspecified_5282482`) instead of pooling them all in one
`_unspecified` voice. In SCAMP's mental model a forked clock is almost always its own
musical stream, much like a voice, so keeping them separate would usually match intent.
Only affects notes the user never gave an explicit voice.

## Playback

### MPE for external MIDI

Full design spec: [`mpe-microtonal-midi.md`](mpe-microtonal-midi.md).

SCAMP's per-channel pitch-bend microtonality renders correctly on FluidSynth (internal,
multitimbral) but collapses on many external synths — a single **sforzando** instance
applies pitch bend **globally**, not per-channel (confirmed 2026-08-04). This hits both
the real-time MIDI stream and `export_to_midi_file`, which share `MIDIChannelManager`. The
same fix — **MPE** — also solves the tangled second problem that many soft-synths ignore
the RPN that sets pitch-bend *range*, which is why external MIDI still defaults to a timid
±2. Big open design question captured in the spec: MPE is inherently **single-timbre**,
whereas SCAMP is a **multi-instrument** ensemble, so mapping an ensemble onto MPE (likely
one zone per port) needs a real decision. Defaults (flag location, ±24 vs ±48, on/off by
default) still TBD.

## Tests & settings

### Test infrastructure & settings refactor

Replace the hand-rolled golden-output runner with pytest + syrupy, add targeted
unit tests for the algorithmic hotspots, and modernize the settings system.
Done in bite-sized steps so each one ships independently.

#### Phase A — Test infrastructure (no behavior changes)

1. **Run existing tests under pytest, unchanged.** Add `pytest` as a dev dep,
   parametrize over the example `.py` files, keep `test_examples.py` working in
   parallel. Also inject fast-forwarding from the harness (an autouse fixture),
   so the example copies don't each have to call it — right now 29/31 do it by hand.
2. **Fix the determinism leak.** `get_example_result` resets
   `engraving_settings` but not `playback_settings` or `quantization_settings`.
   Reset all three.
3. **Replace hand-rolled `.json` snapshots with `syrupy`.** Migrate one example
   first to feel out the workflow, then bulk-convert. `--snapshot-update`
   replaces the `-s` flag.
4. **Retire the old `test_examples.py` script.** Delete it once syrupy +
   pytest cover everything. Update CLAUDE.md.

#### Phase B — Targeted unit tests

5. **Pick 2–3 algorithmic hotspots and write real unit tests.** Candidates:
   tricky quantization cases, tuplet nesting, microtonal channel allocation.
   Build a small `Performance` by hand, call the function, assert. No clocks,
   no soundfonts.

#### Phase C — Settings refactor

(The dataclass conversion and the general `"auto"`-settings resolver mechanism
this builds on are both done — see the changelog.)

6. **Stop auto-rewriting JSON on load.** Split "load + fill defaults in
   memory" (silent) from "migrate file on disk" (explicit, on version upgrade
   or via a CLI command).
7. **Let `Session` accept a settings override.** `Session(playback_settings=…,
   quantization_settings=…)`. Globals stay as the default for top-of-script
   ergonomics, but a Session can carry its own. Real test isolation; makes
   "what settings did this Performance use?" answerable.

## AI tutor & workspace home

### Build out the AI SCAMP tutor

Status: ongoing. The AI tutor lives in `scamp_tutor/` (instructions, fetch-on-demand
doc bundles, example bundles) and is hosted at scamp.marcevanstein.com/aitutor/. It's
currently **homeless version-control-wise** — folding it into the mega-repo (below)
is part of that plan. Full context in
`.claudeConvos/2026-07-15-scamp-tutor-stumbling-blocks.md`.

The work is maturing the tutor so it stops making SCAMP mistakes and reads well:

- **`stumblingBlocks.txt`** — a category-organized list of non-obvious API facts
  (blocking/timing defaults, `play_note` arg traps like list = gliss not chord and
  `length` not `duration`, soundfont preset-name mismatches, envelopes, notation),
  fed to the tutor as required up-front reading. Marc keeps a running list of observed
  AI failures in `scamp_tutor/aisux.txt`; new entries flow into stumblingBlocks.
- **Correct against the current API** — legacy training-data traps: `fork()` no longer
  injects the child clock as the first arg (teach `current_clock()`); bare-number
  `set_tempo_target(100, 9)` is rejected (needs `Moment.after_beats(9)`).
- **Brevity** — Marc found the tutor wordy; instructions now lead with "BE BRIEF".
- **Example bundles** — regenerated from example sources by
  `scamp_tutor/regenerate_bundles.sh` (runs the index generator first), so they track
  the examples folder. (The examples reorg + generated `INDEX.md` that feed these
  landed 2026-08.)
- **Server-side loose ends** (from `aisux.txt`): upload updated files to
  scamp.marcevanstein.com/aitutor/; fix robots.txt.

### Workspace mega-repo via git submodules

Status 2026-07-19: leaning yes, not yet implemented. Full discussion — requirements,
rejected alternatives (glue-only root repo, true monorepo, manually pinned
submodules) — in `.claudeConvos/2026-07-19-workspace-root-github-repo.md`.

The plan: the workspace root becomes a GitHub repo (superproject) with the five
package repos as submodules, so `git clone --recurse-submodules` hands someone the
whole interconnected workspace while each package keeps its standalone repo,
identity, and one-directional independence. The superproject absorbs what's
currently homeless at the root: the uv-workspace `pyproject.toml` + `uv.lock`,
`CLAUDE.md`, `release.sh`, `uploadDocs.sh`, `scamp_tutor/` (in no repo at all
today), and probably `.claudeConvos/`.

Key design points:

- **Submodule pointers are rough convenience, not reproducibility pins** —
  per-package releases are already tagged in the sub-repos. A scheduled GitHub
  Action in the superproject (`git submodule update --remote`, commit, push, daily)
  keeps them fresh with zero manual chore. No other CI: the superproject builds and
  releases nothing.
- **The AI-tutor material consolidates there** — `scamp_tutor/` plus the generated
  bundles currently sitting untracked in this repo (`examples/_bundles/`,
  `examples/INDEX.md`, `docs/build_text/`, `docs/tutor_project_instructions.md`),
  deliberately left uncommitted here (2026-07-19) pending the move. Fetchability
  via GitHub Pages or raw-content links, linked from scamp's README/docs.
- **Docs tooling is workspace-scoped, not scamp-scoped** — the docs cover all five
  packages and deploy from the root (`uploadDocs.sh` rsyncs `scamp/docs_build` to
  scamp.marcevanstein.com).

Open questions: public vs. private (public is needed for tutor fetching, but
exposes `.claudeConvos/` — skim the notes before any first push, and update
CLAUDE.md's "local-only" claim); whether `scamp_tutor` should instead fold into
scamp's docs build (better discoverability, but couples tutor updates to scamp
releases); auto-bump cadence (daily seems fine).

## Assorted fixes

- Audit explicit `clock=` kwargs on `play_note` / `play_chord` / `play_note_from_pitch` (`instruments.py`) and `PerformancePart.play` / `Performance.play` (`performance.py`). Originally added for flexibility, but the only legitimate caller for `blocking=True` is `current_clock()` — anything else means waiting on a clock from the wrong thread, which clockblocks 1.0 will reject with `WrongThreadError`. Consider removing the parameter entirely (or restricting it to `blocking=False` use only). Think about the run_as_server() case though?
