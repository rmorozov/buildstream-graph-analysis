# UX-409: the configure tax names one payer twice

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** anyone reading a cache-logs finding | **Topic:** analysis

## Motivation

Round 64's Plane 3 pass over 79 kept logs:

```text
[medium] configure-tax: ... paid most by codegen.bst, core.bst,
codegen.bst, lib-f.bst
```

Four slots, three elements. `tools/bst_cache_logs.py:638` builds
`payers` from the top-4 per-**log** payers without deduplicating by
element, so any element with two expensive configures (codegen.bst
was built more than once in the kept history) occupies two slots and
pushes a real fourth payer out of the sentence.

## Required Fix

Aggregate configure cost per element before ranking (sum, not
first-seen), then take the top four distinct elements. The same
audit applies to the neighbouring per-log rankings in the file —
one pass over the module for any other `[:N]` taken before a
group-by.

## Out of Scope

- The developer-tax ranking — the walk read it and its grouping is
  already per-element; nothing to change there.
- Widening the finding beyond four payers — four distinct is the
  fix; the count stays.

## Acceptance Test

- A fixture log tree with one element configuring expensively twice
  and four distinct payers: the finding lists four distinct
  elements, the duplicated element once with its summed cost.
- Falsification: revert to per-log slicing — the fixture guard goes
  RED with the duplicate visible in the message.
