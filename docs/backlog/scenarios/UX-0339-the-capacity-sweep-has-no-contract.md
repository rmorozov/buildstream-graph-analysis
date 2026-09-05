# UX-339: the capacity sweep has no contract

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-328 (which found it), UX-190 (the rule it breaks) | **Serves:** R5 — capacity operators, and every payload consumer | **Topic:** contracts | **Area:** bga

## Motivation

Found while enrolling `UX-328`'s three emitters, and it is the
same defect one turn worse. `bga sweep --format json` prints a
document with **no `schema:` key at all**, and `bga sweep
--schema` answered `analyze/v2` — a contract whose four required
keys the document has **none** of:

```text
sweep's keys      calibration_capacities, capacity_model_caveat,
                  knee_points, monotonicity_violations, resource, sweeps
analyze/v2 needs  schema, run_id, total_duration_us, section
present           0 of 4
```

A missing answer sends a reader to look; a confidently wrong one
sends them to write a parser against a shape that does not exist.

`UX-328` de-enrolled it, so the tool now says what is true — *"that
document carries no schema id yet"* — and the guard holds the
absence rather than letting it drift back. That is the honest
stopgap, not the fix: `bga sweep` is `R5`'s command, its output is
the capacity answer, and it is the one document in the tool a
consumer cannot version-check.

## Required Fix

`sweep/v1`: the document declares its id like every other, with
`schemas.py` carrying the types, units and view-hints — the
`resource` it swept, each capacity's makespan and normalized
improvement, the knee points, the monotonicity violations, and the
calibration the projection used (which is the part a reader most
needs qualified). `bga sweep --schema` enrols and answers with it.
`UX-328`'s emitted==answerable guard then covers `sweep` by
existing, and `NO_CONTRACT` in that guard empties — the guard
already reddens if this lands without the enrolment, which is why
no new guard is needed here.

## Out of Scope

- Changing what `bga sweep` computes. This is the envelope, not
  the number.
- The viewer drawing it. `store-aggregate/v1` earned a drawing in
  `UX-234` on its own item; this one can too.

## Acceptance Test

`bga sweep --format json | jq -r .schema` is `sweep/v1`; `bga
sweep --schema` prints that contract and `UX-328`'s equality
clause covers it with `NO_CONTRACT` empty; mutation: drop the
enrolment → the emitted==answerable clause reds naming `sweep`.

## Outcome (round 49, 2026-08-27) — 🟢 Done

### The gap, measured

`UX-328` had already de-enrolled it, so the *wrong* answer was gone and
the *missing* one was all that was left. At `ff69e27`:

```text
$ bga sweep RUN --resource PROCESS --format json | head -3
{
  "resource": "PROCESS",
  "sweeps": [

$ bga sweep --schema
Error: `--schema` is available on analyze, blast, compare, correlate,
  diagnostics, floors, graph, replay, snapshot --aggregate,
  snapshot --list, utilisation, whatif.
  `bga sweep --format json` prints a capacity sweep: `resource`,
  `sweeps`, `knee_points`, `monotonicity_violations` and the
  calibration it used, and that document carries no schema id yet -
  so there is no contract to print. UX-339.
exit 2
```

Eleven contracts, twelve documents. `R5`'s command was the one whose
output a consumer could not version-check, and the guard from `UX-328`
held that absence in a set named `_EMITS_NO_CONTRACT` with one entry
in it.

### After

```text
$ bga sweep RUN --resource PROCESS --format json | head -3
{
  "schema": "sweep/v1",
  "resource": "PROCESS",

$ bga sweep --schema | head -4
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "bga sweep RUN --format json",
  "description": "What more capacity would buy: one makespan per
    capacity tried, the knee past which more buys little, and the
    capacities where the model contradicted itself. A replay over
    already-observed durations, so the caveat travels with the numbers
    rather than beside them.",
exit 0
```

`_EMITS_NO_CONTRACT` is `{}` and `NO_CONTRACT` in the guard is `{}`,
with a clause that says so on purpose — an empty exemption set that
nobody asserts is empty is an exemption set waiting to refill.

```text
tests/unit/test_every_emitted_contract_is_answerable.py
    14 passed  (was 12 passed, 2 skipped)
```

The two skips were an empty `parametrize` over `NO_CONTRACT`, which
reports as a skip and reads as "not run yet" rather than "nothing to
run". They are loops now, plus the emptiness assertion.

### Why the contract has the shape it has

`sweeps` carries the view-hints, because it is the one key a reader
reads as a *table*: `RAIL: "prove"` (the sweep is the evidence behind
a capacity recommendation, never the recommendation), a `QUESTION`,
and three columns with their quantities. The hint that matters most is
prose rather than structure — `normalized_improvement` is a **step**
gain and not a total, and reading it as a total is the exact mistake
the column exists to prevent.

`calibration_capacities` is required rather than optional for the same
reason `capacity_model_caveat` is: empty means *every point on the
curve is a projection*, and a key that disappears when it is empty
makes "no calibration" indistinguishable from "an older build that
never published it".

### The second defect, found by this item's own mutation

M4 removed `calibration_capacities` from the required map and left its
view-hint behind — a contract that describes a key it does not have.
`_check_hint` catches that, and the error a developer saw was:

```text
KeyError: "unknown schema 'sweep/v1' - this tool produces analyze/v2,
           blast/v1, compare/v1, correlate/v1, store-aggregate/v1,
           store/v1, sweep/v1, whatif/v1"
```

A message that **names the thing it says it does not know**, because
`schema()` was `return _SCHEMAS[name]()` under one `except KeyError`
and could not tell a missing registry entry from a builder that threw.
The lookup and the build are separate statements now:

```text
KeyError: "sweep/v1: view-hint for unknown key 'calibration_capacities'"
```

### The export bound, restated with the measured split

Measured on a checkout whose path is the same length as this one's, so
the numbers are comparable to round 48's rather than to a temporary
directory (`UX-287`: the export embeds the run's absolute path at
~5 B/char, so a bound is only readable next to a path length):

```text
                  round 48    UX-338    UX-339
page               227,498   228,528   228,528    (+1,030, +0)
data (golden)       98,986    99,291   101,906      (+305, +2,615)
golden             326,484   327,819   330,434
macro_micro        365,920   367,255   369,870
```

`UX-339` moved the page by **zero bytes** and the payload by 2,615 on
both runs: `sweep/v1` is the twelfth document in the embedded
inventory and no line of viewer source knows it exists. A single
ceiling could not have told that from 2,615 B of new code; the split
can, which is the whole argument for keeping it.

### Mutations verified red and reverted (5)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | drop `"sweep": schemas.SWEEP` from `_SCHEMA_BY_COMMAND` — the filing's own | 2 failed, 12 passed: `test_each_emitter_answers_with_the_id_it_emits` with `{'sweep': ('sweep/v1', None)}`, and `test_answerable_plus_file_written_is_every_contract` naming `sweep/v1` as neither answerable nor declared |
| M2 | drop `'schema': schemas.SWEEP` from the emitted document — the opposite direction, so the fix is a pair and not a rename | 1 failed, 12 passed, 1 error: the `emitted` fixture on `UX-190`'s precondition, and `test_the_sweep_now_answers_with_a_contract_that_fits` |
| M3 | add a required `knee_capacity` the document does not carry | 1 failed, 13 passed: `…_a_contract_that_fits`, `['knee_capacity']` |
| M4 | drop `calibration_capacities` from `_SWEEP_REQUIRED`, leaving its hint | 1 failed, 19 passed, 2 errors — and the message it printed is the rider above |
| M5 | collapse `schema()`'s lookup and build back into one statement | 1 failed, 1 passed: `test_a_contract_that_raises_while_building_does_not_say_unknown` |

### Deviation from the Required Fix

- **A release was cut, which the item did not ask for.** The ledger
  guard's newest-row clause is strict equality between the recorded
  contract state and this tree's, so a twelfth contract makes `0.2.0`
  false the moment it lands. `docs/contributing/release-guide.md`
  §"When to cut one" names exactly this — a new contract — and review
  4 sits at closed-row marker 318, well past `0.2.0`'s 243, so the
  documentation condition was already met. `0.3.0`, kind `extending`,
  derived and not chosen.
- **The changelog's `commit` column is dropped**, for the reason
  `UX-332` dropped the review log's: `fac9618` is a real object in
  this clone and **not an ancestor of `origin/main`**
  (`git merge-base --is-ancestor` says so), so it identifies a commit
  on the author's machine and nowhere else. A release row also cannot
  honestly carry its own commit's hash — the hash covers the row.
- **`PAGE_BUDGET_B` moved from 230,000 to 231,000** although it was
  green at 228,528. Round 48 wrote the convention into the file — ~2.5
  KB of headroom, because a budget with less than one round's growth
  left reddens next round whatever that round does — and 1,472 B is
  under it. Stated here rather than done quietly.
- Everything else is as filed. No new guard was needed for the main
  clause: `UX-328`'s union reddens on the enrolment by existing, which
  M1 confirms.
