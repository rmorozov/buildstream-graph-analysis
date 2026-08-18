# UX-96: the baseline set exists, but assembling it is a scavenger hunt

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-81 (done)

## Motivation

UX-81 delivered exactly what it promised: per-run refs, three
same-config incremental fdsdk captures, and a live band-mode compare
that verifiably replaced the fixed 1% rule with a measured MAD band
(−0.8% correctly absorbed as noise). Doing that in round 11 took: one
`git ls-remote` to discover the refs, three `git archive` extractions,
two manual untars (the two older refs predate the uncompressed `run/`),
and a five-path `bga compare` invocation assembled by hand. That is a
scavenger hunt, and it is the workflow every CI owner is now expected
to run on every candidate build.

Two adjacent gaps surfaced by the same exercise:

- **Nothing checks the baseline set's own homogeneity.** The three
  captures were produced by three different `bga` revisions
  (recorded in each `capture-context.txt`, consulted by nothing).
  Capture-tooling drift inside a baseline set silently widens or biases
  the band — the exact class of unlike-things comparison `bga` refuses
  everywhere else.
- **Cold captures accumulate only by hand.** The weekly schedule
  dispatches the default (incremental) mode; cold history is n=1, so a
  cold baseline set — needed before any cold-vs-cold gate — has no
  automatic path to existence.

## Required Fix

1. A `bga baseline` helper (or `bga compare --baseline-refs <glob>`)
   that, given a repo remote and a ref glob
   (`captures/fdsdk/953683fb-incremental-b4j4-*`), fetches the newest N
   run directories (untarring where a ref predates the uncompressed
   `run/`), verifies they are same-config and same-mode, warns on
   `bga`-revision drift across the set, and runs the band compare
   against the named candidate — one command, suitable for a CI step.
2. Schedule the cold mode too, at a lower cadence (e.g. monthly, or
   alternating weeks), so a cold baseline set exists by accumulation
   rather than by someone remembering.

## Out of Scope

- Any change to the band arithmetic (verified working).
- Cross-forge portability (GitHub refs are the one publication channel
  today).

## Acceptance Test

From a bare clone with the refs present: one documented command
produces the band verdict for a candidate against the newest 3
incremental captures, including the two tarball-only older refs, and
prints a drift warning naming the differing `bga` revisions. After two
scheduled cycles, at least one cold capture exists that no human
dispatched (verify from the Actions ledger).
