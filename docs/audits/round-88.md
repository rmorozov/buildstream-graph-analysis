# Round 88 — the eight open rows, five tracks wide (2026-09-04)

Round 87 left eight rows open. This round took all of them, plus the
one its own work order dropped, plus the architecture review the
cadence guard called due. Ten rows closed, five filed.

## What landed

| | | |
|---|---|---|
| `UX-636` | eighty published keys no document names | Medium |
| `UX-637` | a shallow clone answers, and does not say so | High |
| `UX-643` | a reader role that demotes rather than hides | Medium |
| `UX-645` | the census floor spends half the width bound | Low |
| `UX-646` | the fragment is one event behind the fold | Medium |
| `UX-647` | a rail click never reaches the view-state writer | High |
| `UX-648` | the jump box names sections the old way | Medium |
| `UX-649` | the spread bound was set on one machine | Medium |
| `UX-650` | nine page-built sections declare no reader | Medium |
| `UX-656` | main is red: a closed outcome is over the cap | High |

Four tracks in parallel on disjoint file ownership, then a fifth for
`UX-650` once the files it needed were free, and architecture review 16
alongside.

## Four rows were closed by disproving their own premise

This is the round's shape, and three of the four premises were the
orchestrating session's own.

**`UX-649`: settling was not the cause.** The row was filed saying the
geometry probe read before fonts and layout settled. Time changes
nothing:

```text
                     390x844   1440x900
as the page lands      8.80x     22.16x
+ 500 ms sleep         8.80x     22.16x
+ scrolled through    45.39x     31.81x
content-visibility    51.43x     39.37x
  forced off
```

`content-visibility: auto` with `contain-intrinsic-size: auto 600px`
means a section never near the viewport reports its **placeholder**
height, so the guard measured what the compositor had painted — which
varies by runner. The near-miss nobody had seen: **8.80x against a
bound of 8** at the narrow viewport. Fixed in the instrument first;
both sibling bounds inherited it and stayed green untouched. Only then
did the bound move, 8 -> 20.

**`UX-637`: the sweep was already closed.** One file, fixed in round
86. Widened by hand to `log`, `describe`, `blame`, `shortlog` it is
two, and the second declines on the **graft boundary** rather than
`--is-shallow-repository`, deliberately. This clone is not shallow, so
the case was built at `--depth 20`, where the guard skips with its
declared reason and neutralising it reproduces the original failure.

**`UX-643`: the map is derivable.** The row was filed expecting
`bga:readers` authored across ~51 sections. Eleven payload sections
get a role from the join of `provenance._CLAIMS`' evidence paths with
`findings.FINDING_READERS` — computed, and the guard recomputes it.

**`UX-650`: nine was thirteen.** The row named nine page-built
sections from a report. Measured, there are thirteen — `band`,
`store-trend`, `blast-tree` and the per-element block were missing,
and `culprits` is in a different file than the row said. Nine now
declare a reader argued at the site; four stay unmapped with the
reason written there, which is `UX-643`'s refusal-to-guess applied
again.

## The shared values, and why each is a sum

Three values were written independently by two or more tracks, and
every one merged **without a conflict** into something wrong:

```text
UNRESOLVABLE       base 58; two tracks wrote 59 each; the truth is 61
the loop figure    468 / 465 / 470 against three trees; the truth is 473
the export bound   480,000 and 482,000 in one round, neither merged
```

The export bound is the instructive one. Two tracks moved it for the
same good reason — it was stale, with 375 B of headroom against a note
claiming ~4.9 KB. Neither figure was the merged one. It was resolved
by keeping the larger, recording both readings, and **not** writing a
third number the session could not reproduce: an attempt to re-measure
gave both fixtures an identical size, which is obviously wrong, and an
arithmetic guess presented as a measurement is the failure this round
kept catching elsewhere.

## What the architecture review found

`UX-655` is the one that matters: `analyze/v6` turned
`parallelism.levels` from integers into records, and the consumer
surface read **199 keys before the bump and 199 after**, because
`_consumer_surface()` reaches one level. The new keys landed below the
population that counts them — so `UX-636`'s register reading zero says
less than it appears.

`UX-653` is the one with a mechanism: a dated log entry said
`analyze/v6` on a day the table carried `analyze/v2`. `git log -G`
shows four bumps sweeping the id forward, because `UX-353`'s guard
demands a retired id sit in a paragraph saying so — and sweeping it
forward is the cheap green. A guard is causing the drift.

## Three mistakes in the work order, all the session's own

- **`views.js`, `element.js` and `questions.js` were given to no
  owner**, so the track holding `UX-643`'s mechanism was forbidden the
  files its Required Fix named. Filed as `UX-650` and fixed in the same
  round once the files were free.
- **"Set Status to Done" and "do not touch README.md" cannot both
  hold**, because the pre-commit hook runs the check comparing them.
  One track kept the prohibition and left its markers red with complete
  Outcomes, which was right.
- **Two figures in a brief were stale**: the volume budget bounds nodes
  at 7,900 for the 11-element class, not 5,500, and the export had
  3,985 B of headroom, not 388. Both were quoted from an earlier
  track's report rather than measured. The track checked and said so.

A fourth, caught by a guard rather than by review: five index rows were
written with topics inferred instead of read, and
`test_the_index_counts_match_the_rows_they_index` reddened. The topic
table derives from the task files and was right; the rows were wrong.

## The suite

```text
make test    24 failed, 6976 passed, 125 skipped
make lint    All checks passed!
```

Every failure is the real-`bst` family — `bst show failed (exit 255)
… Cache too full` — which this sandbox cannot run and CI can.
