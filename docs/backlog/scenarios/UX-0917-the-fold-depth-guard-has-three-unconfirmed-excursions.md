# UX-917: the fold-depth guard has three unconfirmed CI excursions, spread over three weeks

**Flake:** tests/unit/test_the_fold_says_how_deep_it_goes.py
**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-691 | **Found by:** `640325d3` appended the third excursion and shipped `main` red — `#248`'s `test (3.12)` failed `test_the_real_ledger_has_no_unfiled_repeat_excursion` on a merge commit whose branch side was green | **Serves:** the round whose push gate is blocked by a file nobody has named | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-691`'s rule is that a file the flake ledger excurses on three times
names itself in a task. `tests/flake_ledger.json` now carries three
unconfirmed excursions for this file and `declared` is empty, so the
guard is red on a clean checkout of `main`:

```text
$ python3 -c "from tools import dev_flake_census as c; print(c.unaccounted(c.load()))"
[('tests/unit/test_the_fold_says_how_deep_it_goes.py', 3)]

run 34778362447  shift 1.538
run 35059653023  shift 1.512
run 35605347763  shift 1.583
```

Two things separate this from `UX-908`, whose excursions were *rising*.
These three are flat — 1.538, 1.512, 1.583, a spread of 0.071 over
three weeks — and they sit just above `CI_DRIFT_FACTOR`'s 1.5. A file
whose true cost is a shade over the record trips whenever the runner
has a slow minute, which is the tier gate's known shape
(`UX-911`'s Outcome: the gate needs 1.5x the record *and* a 5s
absolute gap, so which file trips depends on the runner's speed that
day). So the question this row answers is not "what regressed" — most
likely nothing did — but "is this file's record simply too low".

## Required Fix

Read the three runs' own `ci_reference.candidate.json` dumps for this
file's `samples`, and decide between the two readings a flat series
allows:

- the record is stale and the file's real cost is ~1.5x it, in which
  case the row closes by refreshing the record from a CI candidate
  (never a local timing — `UX-912`);
- the file really is bimodal, in which case name what makes it slow
  and either fix that or `declare` it in the ledger with the reason.

Either way the row names the file, which is what clears `UX-691`'s
guard today.

## Out of Scope

`UX-908` and `UX-890`, the other two unfiled-excursion rows, which are
their own files. Changing `CI_DRIFT_FACTOR` or `CI_DRIFT_SECONDS` —
`UX-911`'s Outcome already measured what they cost and this row is one
file, not the gate's shape. Refreshing the whole reference, which is
`UX-912`.

## Acceptance Test

`python3 -c "from tools import dev_flake_census as c;
print(c.unaccounted(c.load()))"` prints `[]` on a clean checkout, and
`tests/unit/test_a_file_with_three_excursions_has_a_filed_task.py`
passes — both already true the moment this file exists, which is why
the row is filed rather than fixed. The measured part is the reading
above: whichever of the two branches the candidate dumps support, with
the `samples` pasted.

## Outcome (round 138, 2026-09-23)

**Round 138, 2026-09-23.** **Premise:** held — the record was stale, and
the flat series is the file's cost, not a bimodal file.

### The gap, measured

The three runs' candidate dumps answer 403 from this container, so the
readings are `tests/ci_reference.json`'s `samples`, which carry CI's own
seconds per run since `UX-924` (`c8b2f781`):

```text
$ python3 -c "import json; r=json.load(open('tests/ci_reference.json'));
  k='tests/unit/test_the_fold_says_how_deep_it_goes.py'; print(r['files'][k], r['samples'][k])"
14.5 [10.94, 10.94, 16.53, 15.0, 14.5]
ledger x shift, on the 10.94 record adopted 2026-09-02 (0d288ebf):
34778362447 16.83s  35059653023 16.54s  35605347763 17.32s  35735148844 17.67s
```

Three real readings 14.5-16.53 and four excursions 16.54-17.67: one band,
14.5-17.7 s, with no reading near 10.94. The record was set once and
could not move until `UX-924`. By run (`UX-936`), its four excursions
had 1, 0, 1 and 2 other files beside them.

### After

`0c166828`, CI's third post-`UX-924` adopt, took the record 10.94 -> 14.5
(`median_low` of the window). Each ledger reading against it:

```text
34778362447 x1.16  35059653023 x1.14  35605347763 x1.19  35735148844 x1.22
over 1.5x and +5s: False for all four
$ python3 -c "from tools import dev_flake_census as c; print(c.unaccounted(c.load()))"
[]
```

Left to CI's adopt: no hand edit to `ci_reference.json` (`UX-912`), and
the two remaining 10.94 copies leave the window in two more adopts.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| A1 | this task's `**Flake:**` field deleted | `test_the_real_ledger_has_no_unfiled_repeat_excursion`, 1 of 8 |
| A2 | `**Flake:**` pointed at `test_tie_break.py`, which has no excursion | the same clause, 1 of 8 |

### Deviation from the Required Fix

The candidate dumps were unreachable: the artifact zip and the
`tier-reference` job log of run 35735148844 both answer
`CONNECT tunnel failed, response 403`. The reference's `samples`
window is the same per-run reading, divided by each run's shift.
