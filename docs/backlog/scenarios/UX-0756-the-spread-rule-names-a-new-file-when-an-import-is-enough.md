# UX-756: the spread rule names a new file when an import is enough

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-632 (the spread), UX-336 (the selector) | **Serves:** the round that re-derives what it was told to and is red anyway | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

`CLAUDE.md` and the fixing guide say the touch-map spread is
re-derived **after any new test file**:

> `dev_touching.py --spread --write` owns the fixing-guide cost row
> (re-derive after ANY new test file)

Round 103 added no test file. It added two *imports* — deriving two
guards' spelling tables from `dev_track_cost.count_word`, so two more
test files name that module and its selection grew. That was enough
to move the figure, and CI reddened on it:

```console
$ # at 0c334ed, before the imports
31-145 of 509 test files, median 37
$ # with the two imports
31-145 of 509 test files, median 38
```

```text
FAILURE tests.unit.test_the_loop_stays_fast.TestTheSelectorStillSelects::
        test_the_selection_is_a_fraction_of_the_suite
the selection outgrew its measured shape: {'median': 38, ...}
```

The rule names a sufficient condition as if it were the necessary
one. What actually moves the spread is a change to *which test files
name which modules* — a new file is only the commonest way to do it.
A round that follows the rule as written re-derives nothing and is
red for a reason the rule told it could not happen.

## Required Fix

1. State the condition that actually holds: the spread moves when the
   set of (test file, module named) pairs changes — a new test file,
   a new import, a renamed module, a deleted file.
2. Say it in the one place that owns it, and let the other repeat it
   by reference rather than by copy — two statements of a rule is how
   the `count_word` table drifted in `UX-752`.

## Out of Scope

- The ceiling itself, and the convention that median sits at the
  measurement. Both are `UX-737`'s and unchanged; round 103 followed
  them and recorded the reading either side.
- Automating the re-derivation in a hook. That is a bigger change
  than the sentence being wrong, and nothing has measured whether a
  round would rather be told than have it done silently.

## Acceptance Test

The sentence names the pair-set condition, a round that adds only an
import is told to re-derive, and the two documents that carry it do
not state it twice.

## Outcome

**The gap, measured.** The quoted sentence ("owns the fixing-guide cost
row (re-derive after ANY new test file)") does not exist verbatim
anywhere outside this task file — checked `fixing-guide.md`,
`CLAUDE.md`, `rules.md`, `.claude/skills/{verify,decompose}/SKILL.md`,
`test_the_cost_row_is_derived_from_the_selector.py`, `dev_touching.py`,
`UX-0730`, `round-103.md`. None state a trigger, narrow or otherwise —
the defect (round 103's imports moved the figure with no new file) is
real, but there was nothing to correct, only something to add.

**The close, measured.** One sentence added to
`docs/contributing/fixing-guide.md` (`SITES` in the guard names this
file as the row's sole owner): "It moves whenever the set of (test
file, module named) pairs changes - a new test file, a new import, a
renamed module, a deleted file - not only the first of those
(`UX-756`: round 103 moved it with two imports and no new file, and CI
reddened on the stale row)." `CLAUDE.md` already deferred ("the guide
carries it") and needed no change; no guard failure message restated
the condition, so none needed to point instead of repeat.

**Demonstration.** Added `from bga import cli` to
`tests/unit/test_a_batch_closes_in_one_move.py` (outside
`select(["bga/cli.py"])`'s 145 files), no new test file:

```console
$ python3 tools/dev_touching.py --spread
31-146 of 510 test files, median 38          # was 31-145
$ python3 -m pytest tests/unit/test_the_cost_row_is_derived_from_the_selector.py -q
2 failed, 9 passed
AssertionError: docs/contributing/fixing-guide.md: 0 line(s) price the
loop at '31-146 of 510 test files, median 38', expected 2. Run
`python3 tools/dev_touching.py --spread --write`.
```

Reverted; `--spread` back to `31-145 of 510 test files, median 38`.

**Mutations.**

| mutation | reddened | count |
|---|---|---|
| import-only change, no new file | `test_each_cost_line_carries_the_figure`, `test_the_document_is_what_the_tool_would_write` | 2 failed, 9 passed |
| reverted | (same guard) | 11 passed |

**Deviation.** None — the sentence landed exactly where `COST_SITES`
already says the row lives; no mechanism change, no second document
touched.
