# Design spec: MPE (and reliable wide pitch-bend range) for external MIDI

Status: **not started** — design only. Written 2026-08-04.

## The problem

SCAMP does microtonality by allocating a MIDI **channel per distinct pitch bend** and
emitting a per-channel pitch-bend message (see `MIDIChannelManager` in `_midi.py`). This
is the classic pre-MPE "multi-channel pitch bend" trick, and it is correct *standard*
MIDI — but it only renders correctly on a receiver that treats channels as **separate
parts** (multitimbral / "Omni Off"), each holding its own pitch-bend register.

- **Internal FluidSynth playback works** (`SoundfontPlaybackImplementation`) because
  FluidSynth is a 16-part multitimbral synth — it honors per-channel bend. This is our
  proof the technique itself is sound.
- **External MIDI does not, on many synths.** A single **sforzando** instance (and any
  monotimbral / Omni-On soft-sampler loaded as one patch) keeps **one global pitch-bend
  register** and applies the last bend it received to *all* sounding voices. Confirmed
  empirically 2026-08-04 with a diagnostic file
  (`examples/Junk Drawer/sforzando_channel_test.mid`): bending channel 1 alone bent
  *every* note. This is not a spec violation — Omni-On mode legitimately discards channel
  identity — it just isn't the mode our technique assumes.

This affects **two** external paths, both of which share `MIDIChannelManager`:
`MIDIStreamPlaybackImplementation` (real-time MIDI out) **and**
`Performance.export_to_midi_file` (offline). So it is a live-playback concern *and* a
file-save concern — fixing one without the other is incoherent. The good news: because
the channel-allocation **policy** lives in one shared class, an MPE policy can too; only
the message **emission** differs per backend (rtmidi vs midiutil).

## Entangled second problem: pitch-bend *range* is unreliable on external synths

There are really two things wrong, and they're tangled:

1. **Per-channel bend not honored** (the global-bend problem above).
2. **Pitch-bend *range* (sensitivity) not honored.** SCAMP tries to widen the bend range
   by sending RPN 0 (`CC101=0, CC100=0, CC6=range, CC100=127`). Many soft-synths **ignore
   this RPN** and stay at their built-in default (usually ±2). If SCAMP has computed its
   14-bit bend values for, say, ±48 but the synth is silently still at ±2, every bend
   comes out **24× too small** — microtones barely move.

Current defaults (in `settings.py`), which encode exactly this fear:

| Path | setting | default | why |
|---|---|---|---|
| FluidSynth | `default_max_soundfont_pitch_bend` | **48** | FluidSynth honors the RPN, so go wide for flexibility |
| External MIDI | `default_max_streaming_midi_pitch_bend` | **2** | ±2 is the universal MIDI default that needs *no* RPN, so it's safe even on synths that ignore RPN 0 |

Marc's actual want: **a reliably-wide range (±24 / ±48) on external MIDI too**, not the
timid ±2. But you *can't* safely widen the range in plain (non-MPE) mode for arbitrary
third-party synths, precisely because you can't count on the RPN being obeyed. So:

> **The reliable-wide-range want and the per-channel-bend want have the *same* answer for
> third-party synths: MPE.** An MPE receiver, by definition, switches into a mode where
> member-channel bend is per-note **and** respects a defined per-note bend range. Getting
> one gets the other.

(Resolution is a non-issue at any of these ranges: 14 bits over ±2 = 0.024¢/step, over
±24 = 0.29¢/step, over ±48 = 0.59¢/step — all inaudibly fine. So range choice is about
*headroom for glissandi*, not precision.)

## How MPE would map onto SCAMP — and the deep tension

MPE (recap): reserve a **master channel** (lower zone → ch 1; members ch 2–16), announce
the zone with the **MPE Configuration Message** (RPN 6 = member-channel count) on the
master, put **one note per member channel**, and per-note bend lives on the member
channels (default range ±48, settable via RPN 0).

To make SCAMP's stream MPE-compliant we'd need, together (any one alone breaks it):

1. **Reserve a master channel.** SCAMP currently starts allocating at channel 0 with no
   reservation; in MPE that channel *is* the global one. Note allocation must start at 1
   (lower zone) and never use the master for notes.
2. **Emit the MCM** on the master channel at stream open / file start (member count =
   however many channels we allocate from).
3. **Pin the per-note bend range** explicitly on member channels via RPN 0 — do **not**
   rely on MPE's ±48 default (that's the whole reason we're here). Or: adopt ±48 as our
   value and compute bends against it.

### The tension that makes this non-trivial: MPE is *single-timbre*, SCAMP is *multi-timbre*

MPE assumes **one instrument** spread across the 15 member channels (a channel is a
"voice slot" for that one timbre). SCAMP's whole model is an **ensemble of many
instruments**, each wanting its own channels for its own microtonality. You cannot drop N
instruments into one 15-member MPE zone and get N timbres — an MPE receiver applies one
patch across the whole zone.

So an MPE export mode is a clean fit for **one microtonal instrument → one MPE synth**,
and an awkward fit for a full ensemble. Realistic options for the multi-instrument case:

- **One MPE zone per port/instance** — each `ScampInstrument` routes to its own MIDI port
  (or its own synth instance), each carrying its own lower-zone MPE. Clean, standard, but
  needs one port per instrument.
- **Split the 15 member channels among instruments** — non-standard; a single MPE receiver
  would still give them all one patch, so this only works if the downstream is actually
  multitimbral, in which case you didn't need MPE.
- **Punt on ensembles** — ship MPE for the single-instrument (or one-port-per-instrument)
  case first, document the limitation.

This is also already a latent bug *without* MPE: two `MIDIStreamPlaybackImplementation`s
pointed at the **same port** both start allocating at channel 0, so their bends collide.
MPE-per-port would incidentally fix that by giving each its own space — but only if each
gets its own port.

## Design sketch (to be refined)

- **A single opt-in flag**, default **off**, honored by both external paths, ignored by
  FluidSynth (already works; no reason to reserve a channel there). Open question below on
  *where* it lives.
- **Policy in `MIDIChannelManager`** (or a thin wrapper): know about a reserved master
  channel and a member-channel window, so allocation and the "which channels exist"
  bookkeeping are shared by stream + export.
- **Two emitter shims** for the actual MCM/RPN bytes: `SimpleRtMidiOut` (live) and
  `midiutil` (export). Same policy, two ~5-line emitters.
- **Range handling:** in MPE mode, always emit RPN 0 on member channels with the chosen
  range; keep computing bend values against `max_pitch_bend`. Consider unifying
  `default_max_streaming_midi_pitch_bend` to match once MPE makes wide ranges safe.

## Open questions / defaults to decide (Marc unsure)

- **Where does the flag live?** `playback_settings.midi_mpe_mode` (global) vs. a
  per-`MIDIStreamPlaybackImplementation` constructor arg + an `export_to_midi_file(mpe=…)`
  arg vs. a `Session`/`Ensemble`-level setting. Leaning: a `playback_settings` default
  that both paths read, overridable per-call.
- **Default range under MPE: ±48 vs ±24 vs ±12?** ±48 matches the MPE default (fewest
  surprises, most gliss headroom); ±24 is plenty for almost anything. Precision is a
  non-issue (see above), so this is taste + headroom. *Marc: "±24/48 whatever" — pick one.*
- **Default on or off?** Off initially (safe; MPE reshapes channel use). Revisit making it
  the external-MIDI default once proven, since the current ±2 default is itself a
  compromise nobody loves.
- **Lower vs upper zone?** Lower (master = ch 1) is the common choice; recommend it.
- **How to handle ensembles / multiple instruments** — the single-vs-multi-timbre tension
  above. Probably: MPE assumes one instrument per port; document, and pair with a
  per-instrument-port story. Needs a real decision before coding.
- **Interaction with the existing `start_channel` arg** on `MIDIStreamPlaybackImplementation`
  and with `max_channels` on export — MPE constrains both.
- **Should we also just verify sforzando's own MPE toggle** and document the
  manual-config path (enable MPE in the synth) as the zero-code answer for users, parallel
  to shipping the feature?

## Things that can ship independently (smaller wins)

- **Always emit the RPN-0 range-set even for the default range.** Currently export only
  sends it when `range != 2`, and the stream only when `max_pitch_bend != 2`. Sending it
  unconditionally helps synths that *do* honor it and is harmless to those that don't
  (they were going to ignore it anyway). Does **not** fix global-bend, and does not make a
  wide range *reliable* on RPN-ignoring synths — so it's a minor robustness bump, not the
  real fix.
- **Document the multitimbral-vs-monotimbral reality** in the microtonal docs: internal
  FluidSynth is multitimbral (works); a single external soft-synth patch usually isn't
  (needs MPE or per-instrument routing).

## Testing

- Keep `sforzando_channel_test.mid` (or regenerate it in-repo) as the manual per-channel
  probe.
- A golden test asserting the byte stream contains the MCM + per-member RPN-0 when MPE is
  on, and does not when off.
- Manual: microtonal chord + glissando through sforzando with MPE enabled, confirming
  independent per-note bend.
