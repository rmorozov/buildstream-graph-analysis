# UX-748: three guards read a narrower population than the sentence they check

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-231 (the direction statuses), UX-511 (a dated block), UX-549 (a derived count) | **Serves:** the reader who trusts a guarded sentence because it is guarded | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

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

## Outcome

**Gap measured.** All three confirmed as filed: `_ITEM` on `UX-675`..`UX-684`
resolved to `{675, 684}` only, so `test_a_partial_is_not_wholly_made_of_closed_filings`
never fired even widened — the range still holds a genuinely-open id
(`684`), so no *existing* clause reddens; the wrong claim is that
`684`'s neighbours are *also* open. `python3 -c "import bga.schemas as
s; print(len(s.schema('analyze/v6')['properties']))"` → 61 against the
document's 60. `real-project.md`'s block has 2 rows under "3
element(s)" with no `(NN.N% of the build)` suffix, confirmed against
`bga/findings.py:637-643` and `UX-086`'s own pasted run (3 rows, every
percentage).

**Close measured.** `python3 -m pytest tests/unit/test_every_direction_names_its_reader.py tests/unit/test_the_verification_log_is_true.py tests/unit/test_a_pasted_guide_block_is_fresh_or_dated.py -q`
→ `83 passed`. `make test` → `7602 passed, 127 skipped, 1 warning in
611.97s`. `make lint` clean.

**Mutation table:**

| guard | mutation | reddened | reverted |
|---|---|---|---|
| `test_a_range_called_open_names_no_closed_filing` (new) | restored `` `UX-675`..`UX-684` are open `` | 1 clause, naming `UX-675..UX-684 called open already has closed [675, 676, 677, 681]` | green, 23 passed |
| `test_the_entry_credits_the_true_schema_size` (new) | restored `60 top-level properties` | 1 clause, naming `analyze/v6 has 60 ... has 61` | green, 30 passed + 1 (see below) |
| `TestATimeConcentrationBlockMatchesWhatFindingsAlwaysPrints` (3 new clauses) | restored the 2-row, no-suffix block | all 3 clauses, naming the 3-vs-2 count, the missing suffix, and the missing date/Cuts | green, 29 passed |

**Guard shape.** For (1), widening `_ITEM`/ranges inside the existing
`wholly-closed` and `landed` clauses either missed the sentence
(wholly-closed: the range still has an open id, so it can't fire) or
reddened an *unnamed* sentence (`landed` widened: `directions.md:1558`,
Direction 18's `` `UX-685`..`UX-692` all closed `` — `UX-689`,
`UX-690` are still 🔴). Left the `landed` clause on literal endpoints
and added a new, narrowly-scoped clause instead. The false sentence
itself is now corrected to name the six that landed and the two that
did not; widening the `landed` clause to expand ranges is `UX-751`. For (3), literally
widening `_blocks()` to every fence would additionally require
`kept, not current`/date/Cuts on the fences that carry no `$ bga`
first line — the filter `_blocks()` applies. The `~36` first written
here was a guess and was wrong in both directions; counted:

```console
$ # docs/guides fences whose first body line is not `$ bga `
cli.md                  24 of  27
real-project.md         16 of  19
what-the-viewer-answers.md   1 of   1
total newly admitted by 'every fence': 41
```

41 across **three** guides, not ~36 across two — reported, not
fixed; a dedicated class reads only the one named block instead.

### Deviation: the acceptance test did not survive being committed

The verifier re-ran the acceptance test with the fix as `HEAD` and got
`1 failed, 82 passed`, not the `83 passed` above. The commit corrects
the schema figure *inside* the Verification Log's newest entry, which
makes it a substantive touch of `architecture.md` — so the entry went
stale about itself the moment it landed, reddening its neighbour
`test_nothing_landed_after_the_commit_the_entry_credits`. That is
round 66's shape exactly: measured in a working tree where the commit
did not yet exist in `git log`. Fixed by re-anchoring the entry to
`UX-748` in the same commit. Now `83 passed`.

The mutation table's `31 passed` for guard 2 had the same cause and
reads `30 passed + 1` above.

### Deviation: the new guard reproduced the defect it closes

`_RANGE_OPEN` required the literal `are open`/`is open`:

```console
$ '`UX-675`..`UX-684` are open'    -> [('675', '684')]
$ '`UX-675`..`UX-684` remain open' -> []
```

`remain open` is already the idiom at `directions.md:1686`, so the
guard written to catch a range narrower than its sentence was itself
narrower than its sentence. Widened to `are|is|remain|remains` with an
optional `still`; mutating the status line to the range form with
`remain open` reddens it naming `[675, 676, 677, 681]`, and the old
regex passed that same input silently. Reverted from a pristine copy.
