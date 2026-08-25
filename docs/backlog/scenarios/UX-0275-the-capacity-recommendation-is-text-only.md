# UX-275: the capacity recommendation is text-only

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-116 | **Serves:** R5 and R7 — the two who consume `analyze/v1` rather than reading it | **Topic:** contracts

## Motivation

Found while documenting the block for `UX-242`, whose Required Fix
assumed `capacity_recommendation` is an `analyze/v1` key a consumer
could "meet in a payload and look up". It is not:

```text
$ bga analyze --schema | jq -r '.properties | keys[]'
attribution  attribution_hints  capacity_verdict  confidence  element_join
element_join_coverage  findings  floors  headline  next_steps  occupancy
pipeline_overhead  plane2_coverage  producer  resource_blast  run_id
run_instance  schema  section  signals  structural  timestamp_agreement
total_duration_us  utilisation  violations

$ bga analyze RUN --plane2 PLANE2.json -f json | jq .capacity_recommendation
null
```

The block is computed (`bga/cli.py:_capacity_recommendation`), rendered
in full by the text report, and dropped on the floor by the JSON
renderer. Its sibling `memory_envelope` — the other half of the same
`--builders` question, computed in the same twenty lines of
`_attach_plane2_capacity` — *is* published, as a key of `correlate/v1`.

So the tool's answer to its own founding question (`UX-09`, `UX-116`:
what should `--builders` and `--max-jobs` be, and which constraint is
the reason) is reachable only by a human reading a terminal. A CI job
that wants to assert "the graph binds below the configured builders" has
to parse the text report, which is the thing `UX-75` exists to make
unnecessary.

This is not a rendering oversight to fix quietly: it is a contract
decision. `analyze/v1`'s versioning rule says an addition does not bump
the version, so publishing it is additive and cheap — but *where* it
belongs is a real question, because `memory_envelope` chose
`correlate/v1` and the two are computed together.

## Required Fix

1. Decide and record which contract carries it — `analyze/v1` beside
   `capacity_verdict`, or `correlate/v1` beside `memory_envelope`. One
   answer, with the reason, not both.
2. Publish it there, with its `constraints` list, `binding_constraint`,
   `recommended_builders`, `change` and `caveat` intact. The caveat is
   load-bearing: a recommendation without it is a number a CI job would
   act on.
3. A guard that the text report and the payload cannot disagree about
   which constraint binds — the failure `UX-83` measured between two
   commands, one level down.

## Out of Scope

- Changing what the recommendation computes. `UX-116` settled that and
  `UX-242` documented it.
- Publishing every other text-only block in one sweep. If the audit
  finds more, they are their own rows; this one is filed because it is
  the answer to the question the tool was built to answer.

## Acceptance Test

`bga analyze RUN --plane2 P -f json | jq .<chosen_key>` returns the
recommendation, `--schema` declares it, and the guard reddens when the
renderer and the text report name different binding constraints.

## Outcome

🟢 **Done.** `analyze/v2` carries it.

```text
$ bga analyze tests/fixtures/macro_micro/run \
    --plane2 tests/fixtures/macro_micro/plane2.json --format json \
  | jq '.capacity_recommendation | {binding_constraint, recommended_builders}'
{
  "binding_constraint": "graph",
  "recommended_builders": 2
}
```

**Item 1, the contract decision: `analyze/v2`, beside
`capacity_verdict`.** Not `correlate/v1` beside `memory_envelope`, for
one reason: `correlate/v1` is the per-element join — one row per element
— and a run-level recommendation is not a row of it. The two are
computed together but answer different shapes of question, and the
recommendation's neighbour is `capacity_verdict` ("was the capacity
right for this build?"), which is already here. The item's own
Acceptance Test names `bga analyze … -f json` as the command that must
answer, which settles it from the other end.

An addition, so no version bump — `UX-190`'s rule, the same one
`UX-249`'s `producer` and `UX-215`'s `element_join` landed under.

**Item 2.** `constraints`, `binding_constraint`, `recommended_builders`,
`change`, `caveat` and `pinned_elements` all published, with the schema
declaring what each one is: the constraint list as records with
`bga:columns` (Constraint / Builders it allows / Why), and the caveat
described as *the sentence a consumer must not drop*. Absent — not
empty — without `--plane2`, the distinction `run_instance` keeps.

**Item 3, the two renderers.** The text report renders this block
through the `capacity-recommendation` finding, which *copies* the
fields out of the recommendation, so drift is possible and only a guard
that reads both catches it. `test_the_capacity_answer_is_published.py`
compares the payload, the finding's evidence and the printed text — all
three name one binding constraint, and every constraint the payload
carries is printed with the same ceiling.

**Two things this turned up that were not in the filing.**

*The provenance chain called it unpublished, which stopped being true.*
`UX-229` listed the four fields as "computed, not published" — an honest
label for a real gap, and a lie the moment the gap closed. They are
evidence now, and `unpublished_inputs` is empty for this claim.

*One of those citations had never resolved at all.* The chain cited
`occupancy.builders`; the occupancy block publishes concurrency, idle
time and horizons, and has never carried a builder count. It cites
`capacity_recommendation.builders` now — a field a reader can open.

*And the first fractional count met the page.* `cores_busy` is an
average over the run, and `bga:quantity: count` rendered it as
`1.603977885512677` — fifteen digits of a number measured to two.
`quantity()` rounds a non-integer count to two places; whole counts,
which are every other one, are untouched.

The section renders in the report's "Was the machine used well?"
chapter, beside `capacity_verdict` — measured on the served fixture:
three constraint rows under named headers, in the same chapter box as
the verdict.

**Falsification.** Six mutations, each asserted to have landed:

```text
P1  the renderer drops the block again        6 of 8 guards red
P2  the caveat is stripped on publication     2 red
P3  the finding names a different binding     the drift guard red
    constraint from the payload
P4  the schema stops declaring it             2 red + 6 errors (the run
                                              refuses its own payload)
P5  the fractional count is dumped raw        the quantity guard red
P6  the chapter entry is removed              GREEN, then red
```

**P6 first passed**, and the guard that now catches it is the point: the
section has a published `bga:rail` of `act`, so `UX-286`'s fallback
files it under "Where did the time go?" and nothing complained. But
`capacity_verdict`'s rail is `prove`, which files it under "How much of
this can I believe?" — the two capacity blocks would answer their one
question from two different chapters. A guard now holds them together,
and it is what P6 reddens.
