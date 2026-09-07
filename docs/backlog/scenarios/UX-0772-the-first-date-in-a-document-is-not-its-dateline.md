# UX-772: the first date in a document is not its dateline

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-744 (the register that reads it) | **Serves:** the round whose register row disagrees with its own document | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`dev_round_register.document_date()` takes a round document's first
`YYYY-MM-DD` as the round's date. A document's first date is often not
its dateline:

```console
$ grep -m1 -o '20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]' docs/audits/round-76.md
2026-09-01          # UX-96's monthly cold cron first fires 2026-09-01
$ git log --all --format=%ad --date=short --grep 'round 76' | sort -u
2026-09-02          # every commit naming the round

$ grep -m1 -o '20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]' docs/audits/round-85.md
2026-09-03          # "Open entered the tree on 2026-09-03", a status-word note
$ git log --all --format=%ad --date=short --grep 'round 85' | sort -u
2026-09-04
```

Neither earlier date has a commit touching that round's rows. The
figure is read as a dateline and is an incidental mention.

`UX-744`'s date guard runs from `FIRST_PRICED_ROUND` (90) on, so it
never sees these two. Its Outcome first explained them as multi-day
rounds whose opening and closing dates differ; verification falsified
that and the Outcome now says so. The exclusion is `UX-666`'s
population boundary, not a difference in kind — which means the guard's
population stops exactly where its failures start.

That is this repository's recurring defect: `UX-573`, `UX-746`,
`UX-748`, `UX-750`, `UX-753`, `UX-761`, `UX-767`, `UX-769` and now
this. The instrument is honest inside its window and the window was
drawn where the readings were clean.

## Required Fix

`document_date()` reads a **dateline**, not a date: the date in the
document's own opening sentence, or a stated field ("Run on ...",
"Opens at ...", a heading's parenthesised date), or nothing.

An unrecognized dateline **reds**, not skips: a document that states
no date of its own is exactly the defect this row is filed on, and a
population filter that skips it silently reproduces that same shape
one layer down (found by verification - see Outcome). A round that
genuinely predates the convention is pinned by name and date in
`NO_DATELINE_WAIVER`, the same shape as `UNPRICEABLE_ROUND_WAIVER` -
never excluded by a numeric boundary.

Then widen the guard's population below round 90 to every registered,
documented round, and make the corpus honest: a round whose date is
recoverable from the register (a recent one, still being written)
gets a real, stated dateline; a round that cannot be rewritten without
touching closed history gets the named waiver instead.

## Out of Scope

- `DATE_MISMATCH_WAIVER`'s round-101 entry. That is a real
  discrepancy with a different cause — retroactive documentation
  commits naming the round a day after the work — and `UX-744`
  pinned it correctly.
- The register's dropped ids column (`UX-744`). It is not coming back
  on the strength of this row.

## Acceptance Test

```console
$ python3 -m pytest tests/unit/test_a_run_is_priced.py::TestARegisteredRoundsDateMatchesItsDocument -q
```

(`-k date_matches` does not collect the population-floor guard below;
the class-scoped selector does.) Green with the population widened
below 90 and the corpus given real datelines; red when a round
document's dateline is edited to disagree with the register, when a
round's dateline is dropped without a named waiver, or when the
population is narrowed back to `FIRST_PRICED_ROUND`.

## Outcome

### The gap, measured

The base `document_date()` (first `YYYY-MM-DD` in the text) already
read rounds 76 and 85 wrong:

```console
$ document_date('76', repo=...) -> 2026-09-01   # register: 2026-09-02
$ document_date('85', repo=...) -> 2026-09-03   # register: 2026-09-04
```

but `_documented_rounds()`'s `FIRST_PRICED_ROUND` (90) floor excluded
both, so the guard passed 15/15 without ever comparing them - the
population stopped exactly where its failures start.

A first pass fixed `document_date()` to read a dateline and dropped
the floor, but filtered the population on `document_date() is not
None` - a **verifier found this reproduced the same shape one layer
down**: rounds 102, 104, 105 and 106 state no recognized dateline and
were silently skipped, exactly like 76/85 before, just moved.

### The close, measured

`document_date()`'s regex is unchanged (three forms: a heading's
parenthesised date, an opening "Run on ..." or "Opens at ..."
sentence). What changed is the population: every registered,
documented round with a real register date, no dateline filter -
and the comparison itself now reds on `None` unless the round is
named in `NO_DATELINE_WAIVER` (dated, reasoned, the same shape as
`UNPRICEABLE_ROUND_WAIVER`). Rounds 102, 104, 105, 106 - real work
with a recoverable date - each got a stated `Run on <register date>.`
opening sentence rather than a regex widened to swallow their prose.
Rounds 75-86 (minus 87-89, already dated) are pre-round-99
audit-cadence documents with no stated dateline; closed history, not
rewritten - named in `NO_DATELINE_WAIVER` instead.

```console
$ python3 -m pytest tests/unit/test_a_run_is_priced.py::TestARegisteredRoundsDateMatchesItsDocument -q
32 passed
```

Round 64 is a related, distinct finding, unchanged - see Deviation.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| M1 | `document_date()` reverts to first-match-in-text | `test_..._document[76]` and `[85]`, named |
| M2 | population narrowed back to `FIRST_PRICED_ROUND` (90) | `test_the_population_reaches_below_first_priced_round` (16 collected, not 32 - `-k date_matches` misses this guard, fixed in the Acceptance Test above) |
| M3 | round 90's own dateline edited (09-05 -> 09-04) | `test_..._document[90]` |
| M4 | round 76 dropped from `NO_DATELINE_WAIVER` | `test_..._document[76]` - proves the design reds an unwaived `None`, not a silent pass |

All four reverted from the clean copy the `falsify` skill's step 1
made; the class-scoped command returns to 32 passed after each revert.

**Found, not fixed (verifier; declined by design)**: `DATELINE_RE`
also matches a `Run on ...`/`Opens at ...` line inside a fenced code
block - a pasted console transcript. Synthetic repro confirms it;
every real `docs/audits/round-*.md` checked, none currently trips it -
latent, not live. Left as is per instruction; file its own row if (1)
above did not close it incidentally (it did not - the regex held).

### Deviation from the Required Fix

(orchestrator)

Note for the close: round 64's document states a dateline (`Run on
2026-08-29`) but the register's own date for it is `"—"` - the commit
naming it (`2b68e37`, "Audit round 64...") is not an ancestor of `HEAD`
on this branch, so `commit_signal()`'s `git log` never sees it. That is
`rounds()`'s reachability, not `document_date()`'s reading, outside
this row's declared surface (`tools/dev_round_register.py`'s
`document_date()` and the test population, not `commit_signal()`).
`_documented_rounds()` excludes round 64 the same way it excludes a
document with no dateline: requiring a real register date before
comparing at all.
