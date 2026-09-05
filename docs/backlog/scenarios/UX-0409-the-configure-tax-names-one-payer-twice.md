# UX-409: the configure tax names one payer twice

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Serves:** anyone reading a cache-logs finding | **Topic:** analysis | **Area:** tools

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

## Outcome (round 65, 2026-08-29) — 🟢 Done

### The defect, reproduced in a fixture

A log tree where `twice.bst` is built **twice** (configures of 9s and
8s) beside four elements built once (12s, 7s, 6s, 5s):

```text
before   paid most by biggest.bst, twice.bst, twice.bst, second.bst
after    paid most by twice.bst, biggest.bst, second.bst, third.bst
```

Four slots, three elements — and `third.bst`, a real fourth payer,
pushed out of the sentence by the duplicate. `twice.bst` leads after the
fix because 9s + 8s is more than any single configure, which is the case
that tells **sum** apart from max and from first-seen: a fix that took
the max would rank it second and would look right on any fixture where
the duplicate's rows happen to be large.

### The filing's Out of Scope was wrong, and the neighbour had it too

> "The developer-tax ranking — the walk read it and its grouping is
> already per-element; nothing to change there."

Measured:

```text
sandbox_tax(...)["top_payers"]
  ['biggest.bst', 'fourth.bst', 'second.bst', 'third.bst',
   'twice.bst', 'twice.bst']
```

`payers.append(...)` sits inside a loop over log **records**, so an
element built twice is ranked twice — the same defect, in the ranking
the filing cleared, and the text report slices that list before any
group-by. `elements_by_toll` groups it: summed work and toll, the share
recomputed from the totals, and `cache_key`/`started_at` dropped rather
than picked from an arbitrary row, because a group of builds has no
single cache key and naming one would be a fact about the sort order.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| A1 | the configure ranking slices the per-log rows again | the no-duplicate clause and the pushed-out clause (2 failed, 6 passed) |
| A2 | `sandbox_tax` ranks per log again | the two developer-tax clauses (2 failed, 6 passed) |
| A3 | the group-by takes the max instead of the sum | the summed-not-maximised clause (1 failed, 7 passed) |

**One clause of mine did not discriminate, and A1 is what exposed it.**
It parsed the payer list with `title.split(".", 1)` — and element names
contain a dot, so it read `"biggest"` and could never see a duplicate.
It now splits on the sentence end, and asserts the count as well as the
distinctness.

### The audit the Required Fix asks for

"One pass over the module for any other `[:N]` taken before a group-by."
Three remain, and each is named in the guard with what it is taken over,
census-style, so a fourth cannot arrive unnoticed: the sandbox tax's
payers (grouped since this item), `views['elements']` (one row per
element by construction of the two-plane join), and a redundancy
finding's own element list (already distinct).

### Deviation from the Required Fix

**One addition.** The developer-tax ranking is fixed too, against the
filing's Out of Scope, because the premise that cleared it is false. The
count stays at four distinct payers, as the filing asks.

### Verification

```text
pytest tests/unit/test_a_finding_names_four_payers.py          8 passed
pytest tests/unit/test_cache_logs.py                          51 passed
make lint                                                      clean
```
