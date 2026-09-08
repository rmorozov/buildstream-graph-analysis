# UX-770: the cost row's median sits on a tie, and the population moves under it

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-756 (the rule that re-derives it) | **Serves:** the branch whose CI reds on a figure its own tool just wrote | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`dev_touching.py --spread` publishes `median 38` into
`fixing-guide.md`; CI, on the same commit, computes `median 37`:

```console
$ python3 tools/dev_touching.py --spread            # this container
31-145 of 515 test files, median 38
# CI run 34143169186, job test (3.11), head 1f6b366:
AssertionError: docs/contributing/fixing-guide.md: 0 line(s) price the
loop at '31-145 of 515 test files, median 37', expected 2
```

The file count agrees (515). Only the median differs, and two
properties make that inevitable rather than surprising:

```console
$ python3 -c "...sizes = sorted(len(select([m])[0]) for m in touch_map())..."
modules: 94
values around midpoint: [36, 37, 37, 38, 38, 38, 38]
statistics.median: 37.5
```

1. **`sizes[len(sizes) // 2]` is not a median for an even population.**
   94 modules, so it returns the upper of the two middle values. The
   true median is 37.5 and the published integer is one of the pair.
2. **The population is measured with `TESTS.rglob("test_*.py")`** — the
   filesystem, not the index — and `--spread`'s guard runs *inside*
   `make test`. Any transient `test_*.py` written under `tests/` by
   another test in the same run joins the population for whoever
   measures after it.

So the published constant sits on a tie, over a set that other tests
can move while the suite runs. One element either way flips it, and the
two sides of a `make test` / CI pair need not see the same element.

This is `UX-503`'s principle arriving at a figure nobody applied it to:
*a number that moves without anyone deciding anything does not belong
in a document*. The range (`31-145`) steers the reader; the median's
integer does not, and it cannot be made stable while it is a tie-break
over a live directory.

## Required Fix

Decide what the sentence should carry, then make the tool write it:

- **Preferred:** drop the median and keep the measured range, which is
  what the guide's own sentence is for — a spread, not a duration.
  `UX-503` and `UX-471` are the precedent for removing a figure rather
  than stabilising one.
- **If the median stays:** compute it with `statistics.median` (so the
  name is true), and read the population from the index rather than
  `rglob`, so a transient file cannot join it.

Either way a guard must show the two sides agree, and the mutation has
to move a *population* element, not just the written text.

## Out of Scope

- The range itself and `UX-756`'s re-derivation rule — both stand.
- The touch map's contents (`UX-524`) and its adopt job. The map is
  tracked and identical on both sides; it is not the variable here.

## Acceptance Test

```console
$ python3 tools/dev_touching.py --spread --write
$ python3 -m pytest tests/unit/test_the_cost_row_is_derived_from_the_selector.py -q
```

green, and still green when a `test_*.py` is created under `tests/`
between the write and the read.

## Outcome

The gap, measured. CI run 34143169186, job `test (3.11)`, head `1f6b366`
— the commit whose local gate was `7729 passed`:

```console
AssertionError: docs/contributing/fixing-guide.md: 0 line(s) price the
loop at '31-145 of 515 test files, median 37', expected 2
$ python3 tools/dev_touching.py --spread     # same commit, this container
31-145 of 515 test files, median 38
```

The close, measured. The median is gone; the range is what the sentence
carries. One module's difference — the smallest perturbation two
environments can disagree by — moves the old figure and not the new:

```console
as committed (94 modules):  '31-145 of 515 test files'   sizes[47] = 38
one module fewer (93):      '31-145 of 515 test files'   sizes[46] = 37
restored (94):              '31-145 of 515 test files'   sizes[47] = 38
```

| # | mutation | reddened |
|---|---|---|
| M1 | drop one module from `touch_map.json` | old figure 38 → 37; new figure unchanged — the population moves, the sentence does not |
| M2 | `write_figure` fed a stale line carrying the retired `median N` | `test_the_rewriter_replaces_a_stale_figure_and_nothing_else` — the rewriter still replaces a whole figure and nothing around it |

`sizes[len(sizes) // 2]` was never a median for an even population: at
94 modules it returns the upper of the two middle values, and the pair
here is 37/38. `statistics.median` is 37.5. Removing the figure was
preferred over correcting it because a corrected median is still a
tie-break over a directory read with `rglob` while the suite runs —
`UX-503`'s principle, applied to the figure that reddened this round.

Deviation: the guard's own fixtures encoded `median N` in three places
and were updated with the format, not around it.
