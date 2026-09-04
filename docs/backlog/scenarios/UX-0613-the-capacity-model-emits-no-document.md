# UX-613: the capacity model emits no document

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-595 (which built it), UX-341 (the quantity rule that blocks it) | **Serves:** R4 and anyone wanting the model's answer in a pipeline | **Topic:** contracts

## Motivation

`UX-595` built the queueing model and `bga snapshot --capacity N,RATE`
prints it. `--format json` is **refused**, and the refusal reads, in
full:

```text
Error: --capacity prints text. Its document carries no schema stamp
yet, and an unversioned JSON payload is what `UX-190` refuses;
`--aggregate --format json` publishes the measured half.
```

**Corrected in place, round 85.** This item was filed quoting a
different sentence — "a stamped contract needs a `rate` member in
`schemas.QUANTITIES` … plus the viewer's `quantityFor` and four census
guards". That sentence is `UX-595`'s *Deviation* section, not the
refusal; the refusal names only the missing stamp and `UX-190`. The
`rate` requirement is real — `arrivals_per_day` is the one numeric
leaf in the document with no member that can describe it — but a
reader running the command does not learn it there.

The refusal is right — `UX-190` forbids an output that does not say
what shape it is, and inventing a quantity to dodge that is worse than
declining. But the model's whole value is a number a pipeline can act
on, and today only a human reading a terminal can.

## Required Fix

`capacity-model/v1` as a stamped contract, with the `rate` quantity
argued against `UX-341`'s rule rather than added beside it — a rate is
not a duration and not a count, and the argument for it being its own
member is what this item owes.

## Out of Scope

- The model's arithmetic and its assumption ledger — done and guarded
  in `UX-595`; this publishes what it already computes.

## Acceptance Test

`bga snapshot --capacity 4,400 --format json` emitting a stamped
`capacity-model/v1`, with `--schema` answering for it.

## Outcome

**Implemented.** `capacity-model/v1` is stamped, emitted and answered
for. Every figure below was run on this tree.

```text
$ bga snapshot --project … --capacity 4,400 --format json    exit 0
  {"schema": "capacity-model/v1", "project": …, "builders": 4,
   "arrivals_per_day": 400.0, "excluded_runs": 0, "host_classes": […]}
$ bga snapshot --capacity --schema
  title "bga snapshot --capacity N,RATE --format json"
$ jsonschema.validate(document, schemas.schema(CAPACITY_MODEL))   True
```

### The `rate_per_day` argument, re-checked

`DIMENSIONS` before this item was five members over five dimensions,
none of them T⁻¹ — `duration_us` would render 400/day as "400
microseconds"; `count` has no denominator, which is what the model
turns on; `ratio` is dimensionless, the defect `UX-341` removed with
`seconds`. So `rate_per_day`, `events per unit time`, naming its time
base because one dimension takes one unit. **M4 confirms it.**

### Mutations

```text
M1  drop `schema` from the document      first-key clause       1 failed
M2  move `schema` to second key          first-key clause       1 failed
M3  drop rate_per_day from DIMENSIONS    every_member_declares  1 failed
M4  add rate_per_hour, same dimension    no_two_quantities      1 failed
M5  release-guide fifteen -> fourteen    derived sentence       1 failed
M6  drop --capacity from _SCHEMA_BY_FLAG answerable union       1 failed
M7  arrivals_per_day quantity -> "rate"  known quantities       1 failed
M8  drop that QUANTITY entirely          census[capacity-model] 1 failed
M9  drop the CONTRACT_RUNS entry         inventory is the list  1 failed
M10 drop builders' QUANTITY              census[capacity-model] 1 failed
```

M8/M10 are the vacuity probes: they redden the `[capacity-model/v1]`
parameter specifically, so the five-run store is censused, not skipped.

### The two export bounds, measured on the merge

The Outcome this replaces said the bundle grows **5,000 B**; it does
not — the bundle carries `analyze/v5` only, so that run read the
*headroom* as the growth. Measured at the gate on `20076f2^1`
against `20076f2`, the tree that ships — the track's own figures were 42 B out on both, taken
on its branch before the round's other merges:

```text
             page      golden     macro_micro   data (golden / mm)
before     304,112    419,960       469,977    115,848 / 165,865
after      304,213    420,045       470,062    115,832 / 165,849
delta         +101        +85          +85        -16 /     -16
```

**+101 B page, −16 B data.** The page half is `bga/viewer/format.js`
alone: without a `rate_per_day` case, `quantity(400, "rate_per_day")`
falls to `default` and renders a bare `400`, dropping the unit the
contract exists to carry. No guard forces that case, so it is a
correctness choice, and it is why the page half may move here.

Both bounds raised — 420,000 → 425,000, 470,000 → 475,000 — with the
split in the note beside them. They had **40 B** and **23 B** of
headroom before this item, so they had stopped being budgets; the new
ones leave ~4.9 KB, the order `UX-483` chose when it last moved one.

### Deviation from the Required Fix

Five surfaces beyond the eleven, each forced by a guard, not chosen:
`docs/design/architecture.md` and `docs/guides/cli.md` (the contract
inventory and the consumer's home — `--capacity` was in **no** guide
since `UX-595`); `docs/contributing/fixing-guide.md`, whose derived
"Part 32 spans" figure moves when a §32.5 row is added; and the two
committed analyses, refreshed by `tools/dev_refresh_analysis.py`
because `producer.contracts` gained an id and `document_shape.leaves`
counts it (699 -> 700, 1067 -> 1068) — the general cost of publishing
a contract, which no task file names.
