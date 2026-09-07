# UX-772: the first date in a document is not its dateline

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-744 (the register that reads it) | **Serves:** the round whose register row disagrees with its own document | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

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
document's own opening sentence, or a stated field, or nothing. A
document with no dateline returns `None` and the comparison skips it
rather than comparing against a cron schedule.

Then widen the guard's population below round 90 as far as datelines
exist, and pin what genuinely cannot be dated rather than excluding a
range.

## Out of Scope

- `DATE_MISMATCH_WAIVER`'s round-101 entry. That is a real
  discrepancy with a different cause — retroactive documentation
  commits naming the round a day after the work — and `UX-744`
  pinned it correctly.
- The register's dropped ids column (`UX-744`). It is not coming back
  on the strength of this row.

## Acceptance Test

```console
$ python3 -m pytest tests/unit/test_a_run_is_priced.py -k date_matches -q
```

green with the population widened below 90, and red when a round
document's dateline is edited to disagree with the register.

## Outcome

(open)
