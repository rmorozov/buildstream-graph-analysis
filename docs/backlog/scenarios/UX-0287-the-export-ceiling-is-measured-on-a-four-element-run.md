# UX-287: the export ceiling is measured on a four-element run

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-195 | **Serves:** R8 — who attaches the file to a ticket | **Topic:** guards

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
