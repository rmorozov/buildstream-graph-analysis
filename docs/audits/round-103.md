# Round 103: the guard whose population is narrower than its sentence, five times

Run on 2026-09-07. A backlog round, ordered by the session:
housekeeping and workflow first, then unblocked analysis, then bugs.
Seven rows closed — `UX-666`, `UX-708`, `UX-742`, `UX-705`, `UX-747`,
`UX-745` by the session, then `UX-746`, `UX-749`, `UX-748` and
`UX-674` by four `implementer` tracks on `sonnet`, each read by a
`verifier` on `sonnet` before its merge. Five rows filed, three of
them also fixed.

The user's standing instruction mid-round — *"dispatch verifiers once
tracks report"* — is what this round is a measurement of. The ledger
showed no round since 95 had done it: thirteen tracks merged unread.

## The one shape, five times

Every track this round hit the same defect class, and so did two of
the fixes for it:

```text
UX-573   (round 83)  the original: a widening that passed vacuously
UX-746   MAPPED_SUFFIXES widened; removing the root reddened nothing
         until a named member was added to the walk clause
UX-748   `_RANGE_OPEN` matched only the literal `are open`; `remain
         open` is already the idiom at directions.md:1686 — the guard
         written to catch a narrow population was narrow
UX-750   the map's one count is `400 lines`; the guard's noun list has
         six nouns and `lines` is not one
UX-753   the flow-axis layout UX-674 added is read by no guard it
         wrote; only a pre-existing overlap test sees it
```

`UX-751` and `UX-752` are the same shape in the tooling: a `landed`
clause reading endpoints where its sibling reads the range, and a
spelling table that ran out at forty while its writer built the word.

## What the verifiers found

Four runs, 546k, and none of these came from the track's own report:

```text
UX-746   the map row called `real-project-capture.yml` manual; it
         carries two crons (`0 3 * * 0`, `0 4 1 * *`) and has since
         before the round's base
UX-749   a 6-line comment against the Register's 1-line cap; the
         `#anchor` shape the widened guard still misses
UX-748   the acceptance test did not survive being committed —
         `1 failed, 82 passed`, not the 83 the Outcome claimed
UX-674   "bumped by exactly the amount my change cost" is false:
         34,389px → 35,813px is 1,424, against a 900 bump that fits
         only because 611px was already unused
```

Two would have merged as defects. `UX-748`'s figure was measured in a
working tree where its own commit did not yet exist in `git log` —
round 66's shape — and `UX-674`'s `~34,678` was a guess 289px wide of
a number no command had produced.

## The gate, and three reds

Three CI reds, all the session's own, all caught by CI and not by the
session:

```text
KeyError: 45          the spelling table (`UX-752`), whose own
                      docstring warned that two tables drift
median 37 → 38        two imports moved the selector's spread;
                      re-derived, ceiling to the measurement
the log went stale    `_only_a_derived_figure_moved` cannot read a
                      merge (`UX-754`): `git show` emits a combined
                      diff, the parser strips one column of two
```

`UX-754` is also the second, unrecorded cause of `UX-748`'s red, which
was attributed to the anchor rule alone.

A local `make test` disagreed with CI twice: 18 errors in
`test_the_journey_has_an_answer_key.py` that CI never sees, on a file
that passes 25/25 alone. First diagnosed as contention with a
concurrent track — wrong; a quiet-box re-run reproduced them. CI
reports `0 errors` on the same commit.

## Agents

| run | shape | tokens | tool calls | wall | the verifier found |
|---|---|---|---|---|---|
| UX-749, citations and a branch count | bounded | 84k | 69 | 19 m | a Register violation; the `#anchor` shape still missed |
| UX-746, four workflows on no map | bounded | 159k | 71 | 22 m | a row misdescribing its workflow's triggers |
| UX-748, three narrow guards | judgement | 413k | 121 | 49 m | the acceptance test did not survive being committed; the new guard vacuous on `remain open` |
| UX-674, the type scale | judgement | 410k | 363 | 104 m | a false budget-cost claim; an undisclosed non-rewrite; a layout change no new guard reads |

Eleven round-103 rows in the ledger, 2,147k across seven
`implementer` and four `verifier` runs (`dev_track_cost.py --ledger`).
The two dearest tracks are also the two whose verifiers found the
most.

## What the next round should read first

`UX-751` and `UX-753` are the two halves this round left open on its
own theme. `UX-744` still stands: no register says which rounds exist,
and rounds 96-102 have no document — this one is written into the gap
rather than closing it.
