# UX-529: the export's data half is unbounded, and holds each row twice

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-360 (the page-half budget), UX-526 | **Serves:** anyone attaching a report of a large project | **Topic:** viewer

## Motivation

```text
                      @1,202       @4,002
report JSON          628 KB      2,042 KB     427 B per element
page half            294 KB        294 KB     PAGE_BUDGET_B 300,000 — holds
export               1.0 MB       2.4 MB      EXPORT_BUDGET_B 8 MiB — reports only
```

`PAGE_BUDGET_B` bounds the hand-written half and `EXPORT_BUDGET_B`
only *reports*, so the data half meets the ceiling at about 13,000
elements with nothing between. And every row past the 40-row bound
is present twice — once in the JSON, once as a hidden `<tr>`
(`UX-526`) — which is the page's largest single duplication.

## Required Fix

The data half gets a budget of its own per size class, asserted the
way the page half is, and the per-element embedding is what pays for
it: the elements table embeds the rendered rows and a reference to
the rest, which the focus path fetches (served) or expands from a
compact form (export).

## Out of Scope

- `EXPORT_BUDGET_B` itself — it stays the outer ceiling.

## Acceptance Test

Data-half bytes at 4,002 pasted before/after; the composition guard
red if the data half exceeds its class budget.
