# UX-955: a population entry keeps the tree size its seconds no longer describe, so the gate scales the growth twice

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-716, UX-803, UX-924 | **Blocks:** — | **Found by:** round 138 — `UX-929`'s reading: `c2fbf2b6` restarted `test_docs_links_and_commands.py` at 34.03 and left its `population` at 737 | **Serves:** every branch that makes the backlog guard slower, which the gate should name | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** test_docs_links_and_commands.py

## Motivation

`UX-716` defines `population` as each entry's tree size "when its
seconds were last set", and `against` scales `expected` by
`population_size() / population`. Since `UX-924`, `adopt` sets the
seconds on every push to `main`, and it never writes `population`:

```text
$ git show <sha>:tests/ci_reference.json    # docs_links: files [samples] population
ad666b2c^   18.54 [18.54, 18.54, 18.55, 18.54, 18.54]   737
c2fbf2b6    34.03 [34.03]                               737   # UX-803 restart
dcbe4615    34.03 [34.03, 35.29]                        737
backlog now (dev_close_task._backlog_counts()['scenarios'])  942
```

34.03 was read on a tree of 934 rows, and is then scaled by 942/737 =
1.28 as if it had been read on 737. Measured with `against()` on the
committed reference, every other file at its record (shift 1.0):

```text
docs_links reading   ratio to 34.03   verdict
50.0 s               x1.47            ok
60.0 s               x1.76            ok
65.0 s               x1.91            ok
66.0 s               x1.94            drift
60.0 s, population set to 942         drift
```

So a 1.9x regression of the backlog guard reads `ok` today, and the
slack grows with every row filed. `test_a_guard_reads_only_what_a_clone_has.py`
has the same shape: `population` 496 against 582 test files now, while
its seconds are re-added by each adopt from a run on the bigger tree.

## Required Fix

Keep `files` and `population` describing the same tree: either `adopt`
normalises each reading to the recorded population before it enters
`samples`, or it records the population beside each sample and
`against` scales by the one `files` came from. Say which, with the
number that chose it. `adopt`'s own `UX-803` step check reads
`over_gate` without the population — say whether that is right too.

## Out of Scope

Which guards belong in `POPULATION_CLASS` (`UX-929`'s Outcome: the
backlog guard's cost per row grew 1.45x, so the population is not its
whole cost). `EXCURSION_FLOOR` and the drift constants.

## Acceptance Test

On the committed reference, a `test_docs_links_and_commands.py`
reading 1.6x its `files` on the current tree is reported by `against`;
a mutation that drops the fix (population left at its recorded value
while `files` moves) reddens a guard that says so.

## Decision

The `architect`, round 140, at `398b4db9`.

```text
Route:     `adopt` rewrites `population` for each POPULATION_CLASS name it samples, through one
           helper shared with `record` (tools/dev_tier_drift.py:481-483), so `files` and
           `population` describe trees at most one window apart (~3 rows, 0.35%, vs the 1.5x)
Rejected:  normalise each reading to the recorded population - pins 737; linear scaling
           compounds against cost per row growing 1.45x (UX-929)
           a population beside each sample, or derived from its sha - a schema change through
           every reader to win back 0.35%
Files:     tools/dev_tier_drift.py; tests/unit/test_an_adopt_keeps_the_population_its_seconds_were_read_on.py;
           tests/quality_reference.json; ci_reference.json is rewritten by the first adopt on records
Guard:     the new file on a reference built by drift.record: population 737, size patched to
           942; after adopt, docs_links at 1.6x files reads drift and 1.2x reads ok
Mutation:  delete the population write in adopt -> 1.6x reads ok (1.6/1.28 = 1.25 < 1.5)
Class:     bookkeeping - removes false greens (docs_links reads ok up to x1.94 today)
Split:     one track; waits for round 141 under the UX-994 cap
Question:  none
```

## Outcome

Gap: `population_for(times)` factored out of `record` (was inline at
`tools/dev_tier_drift.py:481-483`, `UX-955`'s own reading) and called
from `adopt` too, merged over the reference's existing map so a name
`adopt` did not sample keeps its old entry. `adopt`'s own `UX-803` step
check (`_next_sample`, `over_gate` on raw `known[name]`) is unchanged -
the Decision's Route does not touch it, and it answers a different
question (has this file's own reading stepped) from the one `against`'s
population scaling answers (has the tree it runs against grown); it is
not itself population-scaled, so a tree-growth-only jump can still read
as a step there - out of scope per the Decision, named rather than
silently left.

Close: `tests/unit/test_an_adopt_keeps_the_population_its_seconds_were_read_on.py`,
5 cases - `python3 -m pytest tests/unit/test_an_adopt_keeps_the_population_its_seconds_were_read_on.py -q`:
`5 passed in 0.68s`. `make lint`: `clean: 577 finding(s) match
tests/quality_baseline.json; ...` (all `still forced`), `LINT_EXIT:0`.
`python3 tools/dev_sizes.py --check`: `sizes ok: 151 file(s) measured`
(after `--adopt --force`, `tools/dev_tier_drift.py file_lines 1518 ->
1535`, 14 cell(s) written to `tests/quality_reference.json`).
`python3 tools/dev_close_task.py --check`: `0 problem(s) over 8
propert(y/ies), 1023 backlog row(s)`. `python3 tools/dev_touching.py`:
46 file(s), `2030 passed, 3 skipped` (one flake,
`test_the_same_report_confirmed_clears_it`, reread alone on this diff
before and after: `1 passed in 5.26s` both times - machine load on a
shared host, not this change).

Mutation table:

| mutation | reddened | count |
|---|---|---|
| delete the population write in `adopt` (`document["population"] = {**...}` in `adopt`) | `test_adopt_rewrites_the_name_it_sampled`, `test_1_6x_reads_drift_once_population_is_current` | 2 of 5 |
