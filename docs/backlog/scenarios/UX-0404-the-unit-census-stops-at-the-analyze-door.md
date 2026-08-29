# UX-404: the unit census stops at the analyze door

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-343 (the census this extends) | **Serves:** anyone reading a whatif or store number outside the page | **Topic:** guards

## Motivation

Round 64's falsification pass on the rounds 47-63 landing found one
scope gap. Removing the unit declaration from an *analyze* hint
reddens five tests — the `UX-343` census works within its walls. But
the same mutation on a *whatif* hint:

```text
remove QUANTITY: "duration_us" from _WHATIF_HINTS["total_duration_us"]
  (bga/schemas.py, ~line 893)

test_every_number_says_what_it_is.py .......... GREEN
test_a_declared_quantity_matches_its_value.py . GREEN
test_one_unit_per_dimension.py ................ GREEN
```

The census walks only the `report.json` (analyze) payload;
`schemas.py` validates that a declared quantity is *valid*, never
that one is *present* on the other emitters. So `whatif/v1`,
`store/v1`, `store-aggregate/v1` and the sweep contract can each
silently lose a unit — the exact defect class `UX-343` closed, alive
one document over.

## Required Fix

Extend the unit census to every emitted contract: for each schema id
the `UX-328` inventory knows, every numeric leaf either carries a
quantity declaration or appears in the census's declared-exempt table
with a reason. The `UX-328` guard already derives the emitter
inventory structurally — the census walks that list instead of the
one document it grew up on.

## Out of Scope

- The page's rendering of units — `UX-343` finished that, and the
  mutation above proves its own scope holds.
- `plane2/v1` — read-only legacy; a censused unit there would demand
  writes to a contract nothing writes.

## Acceptance Test

- Falsification: the whatif mutation above goes RED under the
  extended census; restore, GREEN.
- The exempt table, if any, names each exemption's reason and goes
  RED when an exempted key gains a declaration (no rotting entries).

## Outcome (round 64, 2026-08-29) — 🟢 Done

### The gap, measured

The census in `test_every_number_says_what_it_is.py` walked
`report.json` and nothing else. Pointing it at each emitter's own
document, before anything was declared:

```text
contract                declared  guessed  neither
analyze/v4                   195        0        2
blast/v2                       6        0        0
compare/v2                    64       13       26
correlate/v2                 314        5        5
store-aggregate/v1            12        0       26
store/v1                       8        0        0
sweep/v1                      22        0        4
whatif/v1                      1        0        0
```

**Seventy-nine numeric leaves outside the analyze door** with no unit
at all or a name-sniffed one — the class `UX-343` closed inside it,
alive in four documents at once.

### After

```text
contract                declared  guessed  neither
analyze/v4                   857        0        2
blast/v2                       6        0        0
compare/v2                   102        0        1
correlate/v2                 348        0        0
store-aggregate/v1            38        0        0
store/v1                       8        0        0
sweep/v1                      56        0        0
whatif/v1                      1        0        0
```

Both remaining `neither` entries are the same excused case in two
documents: a provenance rule whose `observed_path` is null compares
against a quantity the finding computes rather than publishes, so no
path names its unit. `analyze/v4`'s two were already in `UNDECLARABLE`;
`compare/v2` quotes the same rule object inside `candidate_diagnosis`
and now has its own one-entry table, with the same anti-graveyard
clause over it.

The analyze count moves 195 → 857 because the census now walks the
**two-plane** fixture rather than the golden four-element run, which is
where `correlate`'s 348 leaves come from too.

### What the declarations had to be

Four of the five gaps were one missing *shared* declaration, not a
scatter of missing ones:

- **`_RUN_INSTANCE_HINT`** — `analyze/v4` declared `started_at_us`,
  `cpu_count` and `memory_bytes`; `correlate/v2`'s `run_instance` was
  `{question, rail}` and nothing under it. The same three fields, the
  same capture, one document over. Now one constant, read by both.
- **`_store_distribution(quantity)`** — the store aggregate's
  distribution shape appeared ten times and every leaf inside it
  (`min`, `median`, `p95`, `max`, `mad`) reached a reader unitless.
  There was nowhere to say what they were: the unit belongs to the
  *figure*, and the shape is shared, so a constant could not carry it.
  Taking the figure's quantity as an argument is what let the shape
  stay shared.
- **`_COMPARED_SIDE`** — `baseline`, `candidate` and `deltas` publish
  the same seven members `floors` does and `compare/v2` declared none
  of them. Read off `_ANALYZE_HINTS["floors"]["properties"]` rather
  than restated, because two copies of a unit is how `UX-341` got two
  units for one number.
- **`_ENVELOPE_POINT`** — the memory envelope declared its *inputs*
  and left `envelope_bytes`, `builders` and `share_of_host` undeclared
  at both the observed point and every projection, which is the half a
  reader quotes.

Two maps keyed by data (`sweep`'s `knee_points` and each row's
`capacity` vector) got `additionalProperties`, which is `UX-343`'s own
answer for a map whose keys cannot be named.

### A contract gap the census found on the way

`compare/v2` emits `baseline_confidence`, `candidate_confidence` and
`cache_churn`, and the contract declared none of the three:

```text
KeyError: "compare/v2: view-hint for unknown key 'baseline_confidence'"
```

That is `UX-190`'s rule, not `UX-343`'s — but it is the same defect one
level up, and a numeric leaf with no schema node has nowhere to hang a
unit on, so the census could not have been extended without closing it.
All three are `None` on a refusal, so they are declared in
`_COMPARE_OPTIONAL` rather than required.

### Mutations verified red and reverted (4)

Counts are what the run printed. Each was applied to the committed tree
and reverted with `git checkout` after the run.

| # | mutation | reddened |
|---|---|---|
| C1 | `QUANTITY` removed from `_WHATIF_HINTS["total_duration_us"]` — **the mutation the filing names**, which left all three unit guards green before this | `test_nothing_renders_from_a_guess[whatif/v1]`, `test_the_walk_reached_the_document[whatif/v1]`; 2 failed, 45 passed |
| C2 | `store-aggregate/v1` deleted from the census's contract table | `test_the_inventory_is_the_contract_list`; 1 failed, 43 passed |
| C3 | `QUANTITY` removed from `_store_distribution`'s `p95` | `test_what_cannot_resolve_is_named_with_a_reason[store-aggregate/v1]`, naming all four `p95` leaves; 1 failed, 46 passed |
| C4 | a `UNDECLARABLE_ELSEWHERE` entry for `deltas.total_duration_us`, which resolves | `test_no_excuse_outlives_what_it_excused`; 1 failed, 46 passed |

C1 is the acceptance test's first clause, and C4 its second. C2 is what
makes the table a census rather than a list: a contract removed from it
reddens instead of going unchecked, which is precisely how four
contracts went unchecked in the first place.

### Deviation from the Required Fix

- The Required Fix says the census should walk the `UX-328` inventory
  itself. It walks a table in this file keyed by contract id, with a
  clause asserting that table's keys **equal** `schemas.names()` — so
  a new contract reddens rather than being skipped. Importing
  `EMITTERS` from the `UX-328` guard would have coupled two test files
  and still needed local entries for `store/v1` and
  `store-aggregate/v1`, which no command prints.
- `plane2/v1` is out of scope by the filing's own text and is not in
  `schemas.names()`, so the equality clause is unaffected by it.
