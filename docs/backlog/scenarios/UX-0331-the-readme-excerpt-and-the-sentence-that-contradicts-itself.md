# UX-331: the README excerpt, and the sentence that contradicts itself

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-139, UX-192 (pasted-output honesty) | **Serves:** R1 | **Topic:** docs

## Motivation

Walk friction 14. The README's quick-start block says the
synthetic report is "small enough to read in full, which is the
point" and then shows ~15 of ~60 lines — and omits the report's
own first Key Finding. That finding is itself a newcomer trap:
"This build is scheduler-bound, not chain-bound: the critical
path is 88% of wall-clock" — 88% *sounds* chain-bound; the
unstated 90% threshold is what flips it, and the sentence reads
as a contradiction until you know the constant.

## Required Fix

The README block either shows the full report or says what it
elides (the UX-192 rule for pasted output); the
scheduler-bound sentence carries its threshold ("below the 90%
chain-bound line") so it explains rather than confuses — worded
in `findings.py` where the provenance record already knows the
constant.

## Out of Scope

- Changing the threshold or the diagnosis logic — the number is
  right; only the sentence around it confuses.

## Acceptance Test

The README's pasted block matches a fresh run of its own command
(guard-diffed, elisions declared); the sentence on the synthetic
fixture names the threshold (asserted), and `--explain`'s record
quotes the same constant.
