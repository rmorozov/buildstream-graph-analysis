# UX-242: the capacity recommendation is documented nowhere

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** — | **Serves:** R1 and R5 — the two who would act on a `--builders`/`--max-jobs` answer | **Topic:** docs

## Motivation

Filed by `UX-237`'s rule on its own first application: this is one of
the three round-28 instances that named the gap.

`bga analyze` computes `capacity_recommendation` (`bga/cli.py:183`,
`_capacity_recommendation` at `:197`) from Plane 2's achieved
parallelism and the host's cores, and publishes it. Measured across the
documentation tree:

```text
git grep -l capacity_recommendation docs/
  docs/backlog/scenarios/UX-0116-…md      (the filing that built it)
  docs/backlog/scenarios/UX-0229-…md      (a later filing quoting it)
  docs/backlog/scenarios/closed.md        (the closed rows)
```

Three backlog files and nothing else — no guide, no spec part, no line
in `architecture.md`. `UX-116` is the tool's founding question
("`--builders` × `--max-jobs`, jointly") and its answer is reachable
only by reading `cli.py` or by finding a closed backlog row.

## Required Fix

1. `docs/guides/cli.md` says what the recommendation is, what it is
   computed from, and — the part that matters — **when it declines to
   make one**, since a missing recommendation currently looks identical
   to an absent feature.
2. The spec names the field wherever `analyze/v1`'s keys are described,
   so a consumer meeting it in a payload can look it up.

## Out of Scope

- Changing the recommendation itself. `UX-116` and `UX-104` settled
  what it computes and this is about saying so.
- `memory_envelope` — its own filing (`UX-243`), because the two decline
  for different reasons and one paragraph covering both would explain
  neither.

## Acceptance Test

`git grep -l capacity_recommendation docs/` names at least one
instructional document; a reader who has the field in a payload and
neither the source nor the backlog can say what it means and why it
might be absent.

## Outcome — 🟢 Fixed & Verified

`docs/guides/cli.md` gained **"How many builders, and what stops you"**,
with a subsection each for this field and `UX-243`'s — separate, for the
reason this item's Out of Scope gives.

The worked example is the committed dual-plane snapshot, so the whole
block is reproducible from a clone:

```text
$ bga analyze examples/06-…/run --plane2 examples/06-…/plane2.json
  Capacity: builders 4 x max-jobs unrecorded on 4 core(s): graph binds at 2, below the 4 configured - more builders contend rather than overlap here
    graph allows 2: the sweep's knee is at 2 builder(s)
    CPU allows 9: 1.60 of 4 core(s) busy at builders=4, i.e. 0.40 core(s) per concurrent element
    memory allows 9: the 9-builder envelope fits in 15.7 GB (measured over 9 element peak(s), so it says nothing above 9)
    Free capacity you already have: core.bst asked its native build for -j1 - a builder slot drawing one core. Fix that before raising anything, then re-measure.
```

Three constraints, the smallest binds, and the guide says what each one
is measured from — the CPU ceiling is `host_cores × builders ÷
cores_busy`, a measured draw per concurrently-building element rather
than an assumption.

**Clause 1's real content was the decline**, and it needed a table
rather than a sentence, because there are five distinct reasons and they
are not interchangeable: no `--plane2`, no recorded host core count, no
builders value in the run context, no runnable capacity sweep, and Plane
2 seeing no CPU at all. Measured, the failure mode this item names is
exactly as described — running the same command without `--plane2`
prints neither line:

```text
$ bga analyze examples/06-…/run | sed -n '18,26p'
  … Waiting off the critical path, worth nothing to fix today: codegen.bst (7s) …
  Efficiency Score: 1.00 (…)
```

No `Capacity:` line, no `Memory:` line, and nothing saying why. The
guide now closes with *"an absent line means this capture cannot answer,
not this tool has no answer."*

**Deviation from the Required Fix — clause 2's premise is false.** It
asked the spec to name the field "wherever `analyze/v1`'s keys are
described, so a consumer meeting it in a payload can look it up". It is
not an `analyze/v1` key:

```text
$ bga analyze --schema | jq -r '.properties | keys[]' | tr '\n' ' '
attribution attribution_hints capacity_verdict confidence element_join
element_join_coverage findings floors headline next_steps occupancy
pipeline_overhead plane2_coverage producer resource_blast run_id
run_instance schema section signals structural timestamp_agreement
total_duration_us utilisation violations

$ bga analyze RUN --plane2 P.json -f json | jq .capacity_recommendation
null
```

The block is computed, rendered in full by the text report, and dropped
by the JSON renderer — while its sibling `memory_envelope`, computed in
the same twenty lines, *is* published, as a key of `correlate/v1`. So no
consumer can meet this field in a payload, and documenting it in the
spec as though they could would have written a false sentence into the
one document that is ground truth.

What was done instead: the guide states plainly that it is a text-report
block and not an `analyze/v1` key, and the contract gap is filed as
[`UX-275`](UX-0275-the-capacity-recommendation-is-text-only.md) — where
it belongs (`analyze/v1` beside `capacity_verdict`, or `correlate/v1`
beside `memory_envelope`) is a contract decision, not a docs one.

**A near-miss worth recording.** `git grep -l capacity_recommendation
docs/` today also returns `docs/contributing/style-guide.md`, which the
filing's measurement predates. It is not a counter-example: that mention
is the *rationale* for `UX-237`'s rule, naming this field as one of the
three mechanisms with no documentation. A document explaining why a
thing is undocumented is not documentation of it, and a guard that
counted it would have closed this item without a word being written for
a reader.

**The guard** — `tests/unit/test_the_builders_question_has_a_document.py`,
12 tests, shared with `UX-243`. It checks the acceptance test both items
wrote (an *instructional* document names the field, not a backlog file),
that each subsection states its decline conditions, and — the half that
rots — that every pasted figure is one the tool produces from the
committed snapshot today. Falsification is recorded in `UX-243`, which
shares the file.
