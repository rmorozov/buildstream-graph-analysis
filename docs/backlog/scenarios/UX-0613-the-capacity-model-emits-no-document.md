# UX-613: the capacity model emits no document

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-595 (which built it), UX-341 (the quantity rule that blocks it) | **Serves:** R4 and anyone wanting the model's answer in a pipeline | **Topic:** contracts

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

**Not implemented. Built, measured green, and reverted** — one required
edit falls in a file another track owned this round. Everything below
was run against a real tree; nothing here is estimated.

### The argument for `rate` holds

`UX-341`'s rule is stated as data — `DIMENSIONS[member] -> dimension`,
and no two members may share a dimension. A rate has dimension T⁻¹,
which none of the five measures:

```text
duration_us  time                  a length of time; 400/day would
                                   render "400 microseconds"
count        cardinality           no denominator, and the denominator
                                   is what the model turns on
ratio        unbounded multiplier  dimensionless; declaring a
                                   dimensioned value dimensionless is
                                   what UX-341 removed with `seconds`
```

The member must name its time base — `UX-341`'s other half is one unit
per dimension, and a bare `rate` would let builds/day and builds/hour
both be `rate`. So `rate_per_day`, dimension `events per unit time`;
a later `rate_per_hour` reddens the dimension guard, which is the
property working.

### What it was measured to cost

```text
$ bga snapshot --capacity 4,400 --format json   exit 0
{"schema": "capacity-model/v1", "project": …, "builders": 4,
 "arrivals_per_day": 400.0, "excluded_runs": 0, "host_classes": [ … ]}
$ bga snapshot --capacity --schema
  title "bga snapshot --capacity N,RATE --format json"
$ jsonschema.validate(document, schema(CAPACITY_MODEL))   True
```

Eleven surfaces, all green together: `bga/schemas.py` (the member and
a 7-key contract, +198), `bga/viewer/format.js` (renderer case and
`UNIT_SUFFIX`), `bga/capacity_model.py` (the stamp, first key),
`tools/bga_snapshot.py` (emit instead of refuse), `bga/cli.py`
(`_SCHEMA_BY_FLAG`), `test_every_number_says_what_it_is.py`
(`CONTRACT_RUNS` + a five-run store, since three is under
`MIN_BASELINE_RUNS`), `docs/README.md` (two counts and a row),
`docs/spec/specification.md` §32.5 (a row and "all nine schemas"),
`CHANGELOG.md` ("twenty-four published contracts"),
`test_the_capacity_model_prints_its_assumptions.py` (the refusal guard
it retires), and `test_the_report_you_can_attach.py`: the schema
bundle grows **5,000 B**, taking golden to 420,087 B over its stated
420,000 and `macro_micro` to 470,104 over 470,000.

### Why it was reverted

```text
$ pytest test_the_process_documents_derive_their_figures.py
E docs/contributing/release-guide.md does not carry the figure the
  tree gives: ['summary of fifteen live contracts']
E these count a population the tree changes, and nothing derives them:
  release-guide.md: 'fourteen live contracts'
```

A new live contract forces `fourteen -> fifteen` in
`docs/contributing/release-guide.md`. That path was another track's
this round, and there is no way to add a stamped contract without it:
`_live_contracts()` is `contracts.ids()` minus the superseded, and the
sentence is derived from it. Landing the rest would have left `make
test` red on two clauses at the batch gate.

### Deviation from the Required Fix

**The whole fix is deferred**, not narrowed: no half of it landed.
Refile with `docs/contributing/**` in the same track, and the eleven
surfaces above are the decomposition.
