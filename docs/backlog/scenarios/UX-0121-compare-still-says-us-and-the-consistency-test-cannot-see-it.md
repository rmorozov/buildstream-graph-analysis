# UX-121: compare still says "Us", and the consistency test cannot see it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-111 (done — this is its unfinished sixth surface)

## Motivation

UX-111 item 1 fixed `Execution On Chain Us` → `Execution On Chain` —
on `analyze`. `bga compare` still renders the raw field name through a
naive `.title()` (`bga/report/text.py:1157`) beside a value formatted
in seconds (`_fmt_us`, `:939-940`), on the one surface a CI reviewer
reads most. The guard test asserts against the **helper**
(`test_report_consistency.py:88-95` checks `_attribution_label`), not
against rendered output — so the test that exists to keep six surfaces
consistent passed while one of the six stayed wrong. That is the UX-85
pattern (a guard bound to the wrong layer) recurring in the round that
was fixing rendering.

## Required Fix

Route compare's attribution-delta rendering through the same
`_attribution_label` path as analyze, and re-point (or extend) the
consistency test to assert against **rendered surfaces**: render all
six on one fixture and grep the actual text for the forbidden raw
labels, so a seventh surface added later is covered by construction.

## Out of Scope

- Any numeric change; labels only.

## Acceptance Test

`bga compare` on any pair shows `Execution On Chain (s)`-style labels,
none ending in `Us`; the reworked consistency test fails when a raw
label is reintroduced into any rendered surface (verified by
mutation); golden compare fixtures updated in the same commit.
