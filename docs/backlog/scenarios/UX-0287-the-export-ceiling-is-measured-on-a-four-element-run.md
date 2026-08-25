# UX-287: the export ceiling is measured on a four-element run

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-195 | **Serves:** R8 — who attaches the file to a ticket | **Topic:** guards

## Motivation

Found while measuring what `UX-277` cost. It cost 743 bytes. What the
measurement exposed is that the ceiling guarding the export has been
blind for as long as it has existed:

```text
                        before UX-277    after   delta   ceiling 260,000
golden (4 elements)           242,263  243,006    +743   OK   <- guarded
macro_micro (11 elements)     280,093  280,836    +743   OVER
```

`test_the_report_you_can_attach.py` asserts `bytes < 260_000` on a
snapshot built from `tests/fixtures/golden/mixed_task_kinds` — **four
elements**. The 11-element fixture committed by `UX-276` already exports
at 280,093 bytes, 20,093 over the ceiling, and no guard has ever looked.

The ceiling exists because an export is a file someone attaches to a
ticket or a CI artifact. That size is driven almost entirely by
**content** — payload rows, element blocks, per-element detail — and the
run it is measured on has four elements. The guard therefore bounds the
one quantity that barely varies: the viewer's own source, which is
inlined identically whatever the run.

This is the shape `UX-274` found in the context map and `UX-276` found
in two round-37 guards: a check whose scope is narrower than its claim.
The number it prints is real; what it is a number *of* is not what the
guard's name says.

**The ceiling itself may also be wrong**, and that is a second question.
It has moved twice on measurement (`UX-269`: 240,000; round 36:
260,000), each time to accommodate the run it was measured against. A
bound that rises whenever it is exceeded is a record, not a limit — and
it should be a function of the run's size rather than a constant, since
a 4,000-element export cannot reasonably be asked to fit a figure chosen
for four.

## Required Fix

1. The ceiling is measured on a run whose size is representative —
   at minimum the committed 11-element fixture, and the bound is stated
   for the run it applies to.
2. The bound scales with what the run holds, or there are several
   bounds, one per committed fixture. A single constant across a 49x
   range of content cannot be right for both ends.
3. If the shipping export genuinely exceeds what an attachment should
   be, that is a finding about `--export` and is filed rather than
   absorbed by raising the number again.

## Out of Scope

- Making the export smaller. That is a real question and a different
  one; this item is about *knowing* how big it is, which nothing
  currently does.
- The 1,202-element synthetic run as a fixture. It is generated rather
  than committed, and committing it would cost more than the guard is
  worth (`UX-189`).

## Acceptance Test

The ceiling is asserted against the 11-element fixture and reddens at
its current 280,836 bytes until a decision is recorded. Adding content
to a run that pushes an export past its stated bound reddens the guard.

## Outcome

🟢 Done (round 39). The ceiling is two bounds now, because an export has
two halves that grow for different reasons.

**Measured across every run this repository can produce:**

```text
run             elements     bytes      data   modules     css   other
golden                 4   250,472    87,563   144,636  16,444   1,829
macro_micro           11   288,404   125,495   144,636  16,444   1,829
synthetic          1,202 1,063,807   900,898   144,636  16,444   1,829
```

**The page is 162,909 B on every run.** That is the number a ceiling can
honestly guard: it grows when *source* grows, and no amount of content
can mask it. `PAGE_BUDGET_B = 172_000` bounds it, and a second test
asserts the page really is run-independent — which is what justifies
splitting the bound at all.

**Each committed fixture has its own total**, stated for the run it
applies to: golden 260,000 (at 250,472) and macro_micro 300,000 (at
288,404). Content can no longer hide behind the page, nor the page
behind content. The 1,202-element run is generated rather than committed
(`UX-189`), so it is measured here rather than guarded.

**The decision item 3 asked for: the export is not too big.** A
self-contained HTML report at 288 KB — or 1.04 MB at 1,202 elements — is
well inside what a ticket or a mail client takes, and
`tools/bga_view.py`'s own `EXPORT_BUDGET_B` of 8 MiB is the bound that
reflects the actual use. The old 260,000 was never a judgement about
attachments; it was the size of a four-element run at the moment
somebody wrote it down, which is exactly why it had moved five times.

**Falsification, and a non-discriminating mutation fixed rather than
counted:**

```text
M1  pad app.js with 20 KB of *comments*  -> nothing moved      <- see below
M1' pad app.js with 20 KB of *code*      -> 4 failed
M2  macro_micro's bound set to 280,000   -> 1 failed, its row only
M3  the page's cost made run-dependent   -> the split's own test
M4  `_embedded` returns 0                -> 2 failed, both halves
```

M1' reddens four rather than one, and that is the structure working
rather than noise: source growth shows in the page budget *and* in every
total, because a total is the page plus its content. M2 moves one row
and nothing else, which is the other half of the same claim - content
growth is now attributable to the run it happened on.

M4 is the check on the split itself: if `_embedded` stopped finding the
embedded documents, "the page" would silently become "the whole file",
and both the budget and the run-independence test say so.

M1 as first written proved nothing: `bga_view.py`'s `_uncommented` strips
whole-line comments when it inlines a module, so twenty thousand bytes
of comment never reach the export. The mutation had to be code. That is
a fact about the export worth knowing — the page budget bounds *shipped*
source, not source as written — and it is why the second form is the one
recorded.

Tests: 3 new, replacing one; every one runs on a committed fixture.
