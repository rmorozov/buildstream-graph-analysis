# UX-331: the README excerpt, and the sentence that contradicts itself

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-139, UX-192 (pasted-output honesty) | **Serves:** R1 | **Topic:** docs

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

## Outcome (round 50, 2026-08-27) — 🟢 Done

### The gap, measured

The block introduced itself as *"small enough to read in full, which is
the point"* and showed **15 lines of an 86-line report**. It had also
already drifted from its own command in two places:

```text
README pasted                       the tool prints
Key Findings:                       Key Findings:
  Confidence: 0.88 (high)             This build is scheduler-bound, ...
                                      Confidence: 0.88 (high)
  ... not the scheduler)              ... not the scheduler (see Dispatch
                                        Occupancy and Critical Path))
```

The missing first line is the report's **own headline diagnosis**, and
it is the sentence this item's second half is about:

```text
$ bga analyze tests/fixtures/golden/mixed_task_kinds --diagnostics
  This build is scheduler-bound, not chain-bound: the critical path is
  88% of wall-clock, so the time is going somewhere other than the chain.
```

88% *sounds* chain-bound. Nine-tenths of the build is on the critical
path and the sentence says the chain is not the constraint. What flips
it is `CHAIN_BOUND_RATIO = 0.9`, and nothing in the sentence could get
a reader there.

### After

```text
  This build is scheduler-bound, not chain-bound: the critical path is
  88% of wall-clock, below the 90% chain-bound line, so the time is
  going somewhere other than the chain.
```

`{bound:.0%}` is formatted from the constant, not written out, so the
number cannot drift from the rule that used it - and `--explain`'s
record already quoted the same constant, which is now asserted rather
than assumed.

The block is verbatim with every cut declared:

```text
[... elided: Confidence, Certified Floors, Attribution Breakdown ...]
[... elided: CPU Utilisation, Advanced Diagnostics ...]
```

and the guard diffs it against a fresh run of the command the README
prints two lines above - **membership, order and adjacency**, so a
clause quietly rewritten anywhere in those lines reddens rather than
only a line that vanishes.

### Mutations verified red and reverted (5)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | drop the threshold from the scheduler-bound sentence - the item's own | 5 failed, 6 passed: both `TestTheBoundSentence...` clauses **and** three block clauses, because the pasted line is the sentence |
| M2 | delete one `[... elided ...]` marker, leaving the jump undeclared | 1 failed, 10 passed: `test_the_block_declares_its_cuts`, listing the eight report lines the block jumps |
| M3 | restore the efficiency line without its `(see Dispatch Occupancy...)` clause - the drift as it actually was | 3 failed, 8 passed |
| M4 | put "small enough to read in full" back over the elided block | 1 failed, 10 passed |
| M5 | state the report's length as 60 lines instead of 86 | 1 failed, 10 passed: `the README says the report is 60 lines; it is 86` |

M3 first failed with a bare `ValueError` from `list.index` rather than
a sentence. A guard whose failure is a traceback makes the reader do
the work the message should have done, so the two clauses that need a
position ask through a helper that asserts membership first - and the
re-run is what the table records.

### Deviation from the Required Fix

- The Required Fix offered *"shows the full report **or** says what it
  elides"*. The second was taken: 86 lines is not a quick start, and a
  block nobody reads teaches nothing. Every cut is marked and the full
  length is stated and derived.
- **The README's line budget moved 263 → 301** (`UX-135`'s 250-line
  target, which the file has exceeded with an annotation since round
  46). The annotation restates the new number and why, which is what
  the guard is for; `UX-330`'s seed paragraph in the same round is most
  of the growth.
