# UX-748: three guards read a narrower population than the sentence they check

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-231 (the direction statuses), UX-511 (a dated block), UX-549 (a derived count) | **Serves:** the reader who trusts a guarded sentence because it is guarded | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

Review 19 found three drifted sentences that each sit **inside** a
guarded document and **outside** the guard's population. The pattern is
one step worse than "a sentence no guard reads": the guard exists, cites
the file, and passes.

**1. A range is checked at its endpoints only.**
`test_every_direction_names_its_reader.py`'s `_ITEM` regex finds the
literal numbers in a status line, so `UX-675`..`UX-684` reads as
`{675, 684}`. Measured: four of the ten ids that range spans are
🟢 Done (`UX-675`, `UX-676`, `UX-677`, `UX-681`) and `directions.md:1424`
still calls all ten open. Because `684` is open, the "wholly closed"
clause never fires. Direction 19 had drifted the same way and was
corrected by hand this round — by hand, because the guard could not say
so.

**2. The verification log credits a commit, never a figure.**
`architecture.md:1066` says `analyze/v6` is *"still at 60 top-level
properties"*; `python3 -c "import bga.schemas as s; print(len(s.schema
('analyze/v6')['properties']))"` → **61** since `UX-740` added
`duration_resolution`. `test_the_verification_log_is_true.py` compares
the credited commit against commits that touched `architecture.md`, so
a schema change that never touches the document is invisible to it.

**3. A pasted block is only fresh if it starts with `$ bga `.**
`test_a_pasted_guide_block_is_fresh_or_dated.py`'s `_blocks()` scans
fences whose first line is `$ bga `. `real-project.md:1110` opens with
prose, so it is in no branch of that guard — and it says *"3
element(s)"* above two rows, with the `(NN.N% of the build)` suffix
stripped from each, where `bga/findings.py:637-643` always appends it.
`UX-086`'s own record of that run shows the missing third row and every
percentage.

## Required Fix

Each guard's population is widened to what its sentence covers, and the
three sentences are corrected from the source that would then hold
them:

- the range regex expands `A..B` to the ids between, or the convention
  becomes "a status line lists ids, never a range" and the guard holds
  that instead — decide on which is cheaper to keep true;
- the verification log's figures are re-derived, not credited: each
  entry names the command that produced it, as the Outcome sections do;
- the freshness guard's population is *every* fence in a guide, with
  the `$ ` requirement moved from "which fences to read" to "which
  fences can be re-run".

## Out of Scope

- Widening the same three guards to documents outside their current
  files. This row is about the population *within* what each already
  cites.
- `docs/README.md:58`'s *"Twenty-five ids"* — correct today, and its
  three sibling sentences are already derived by
  `TestTheIndexCountsWhatItReadsAndNeverWrites`; adding the fourth is
  that class's own small extension, not this row's.

## Acceptance Test

Each of the three sentences, as it stands today, reds its guard.
Mutation, per guard: correct the sentence and the guard greens; move
the underlying population by one and it reds again naming what moved.
