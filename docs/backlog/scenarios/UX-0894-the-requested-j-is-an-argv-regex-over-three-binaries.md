# UX-894: the requested -j is an argv regex over three binaries, not the element's resolved width

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-32, UX-377 | **Found by:** round 131, [`docs/design/in-step-parallelism.md`](../../design/in-step-parallelism.md) §6 item 4 — filing it showed `graph.json` already carries the resolved number, so this is a join and not the capture change the document costed it as | **Serves:** R2 (the recipe author whose element is scored against the width it was actually given) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

`per_element_parallelism.requested_jobs` is `-j(\d+)` matched against
the argv of `make`, `gmake` and `ninja`, highest wins
(`_REQUESTED_JOBS_RE`, `tools/bst_native_build_tracer.py:3998` and
`:4089-4099`). The element's resolved `max-jobs` is in the same
snapshot: `UX-377` put it in `graph.json` per element, because
`--max-jobs` reaches a command line on exactly one of its three routes.

The denominator is a per-invocation flag, so the published ratio can
exceed 1.0 on an element BuildStream declared `notparallel`:

```text
$ python3 - <<'PY'
import json
g = json.load(open("tests/fixtures/macro_micro/run/graph.json"))
p = json.load(open("tests/fixtures/macro_micro/plane2.json"))
res = {e["uid"]: (e["max_jobs"], e["notparallel"]) for e in g["elements"]}
for x in p["per_element_parallelism"][:2]:
    n = x["element"]
    print("%-12s graph.max_jobs=%-3s notparallel=%-5s regex=%-3s peak=%-3s achieved_vs_requested=%s"
          % (n, res[n][0], res[n][1], x["requested_jobs"],
             x["peak_work_concurrency"], x["achieved_vs_requested"]))
PY
core.bst     graph.max_jobs=1   notparallel=True  regex=1   peak=2   achieved_vs_requested=2.0
codegen.bst  graph.max_jobs=4   notparallel=None  regex=4   peak=4   achieved_vs_requested=1.0
```

`core.bst` is `notparallel`, ran two overlapping work processes, and
scores 2.0 against a width of one. The two sources agree on every
element of this fixture, which is why the regex has survived: it is
right wherever the recipe writes the same number the element resolved,
and silently absent or wrong wherever it does not — an element whose
build system is neither make nor ninja gets `None` and no ratio at all.

## Required Fix

Read the element's resolved width from `graph.json` (`max_jobs`,
`notparallel`) and use it as the denominator, keeping the regex value
as the recipe's own request. Two numbers that can disagree are two
fields, not one: publish both and name which the ratio divided by.

`notparallel` is a width of one and is not a missing value; an element
with no resolved width still gets no ratio rather than a ratio of one.

The join is in `tools/bst_native_build_tracer.py`
(`compute_per_element_parallelism`, `:4037-4153`), reading the
`graph.json` the snapshot already carries; the two fields are declared
in `bga/schemas.py` beside `requested_jobs`.

Where the ratio now exceeds 1.0 it is reporting overlap the element was
not granted — that is a finding about the sandbox, not a parallelism
score, and it belongs in `findings` rather than in the ratio.

## Decomposition

surfaces: `tools/bst_native_build_tracer.py` (`compute_per_element_parallelism` and `_REQUESTED_JOBS_RE`'s consumer), `bga/schemas.py` (the resolved width, the recipe request, and the field naming the denominator)
guards: `test_the_width_comes_from_the_graph_not_the_argv.py` (new)
gap: `tests/fixtures/macro_micro` agrees on every element, so the disagreement case needs a fixture built for it — an element resolved to 8 whose recipe writes `-j2`
track: independent of UX-891, UX-892 and UX-893
gate: not yet scheduled

Input classes: graph width and recipe `-j` agree → today's number, now
with a stated denominator; they disagree → the graph wins and both are
published; `notparallel` → a width of one, not a missing value; no
`graph.json` width for the element → no ratio, as today; no make or
ninja in the element → the recipe request is absent and the ratio is
still computed.

## Out of Scope

Removing `requested_jobs` — the recipe's own `-j` is what a recipe
author edits, and it stays published. Changing `graph.json`, its
producer, or `native_max_jobs_source`. The CPU-weighted denominator
(section 2 of `in-step-parallelism.md` measures process overlap and CPU
disagreeing by 1.5-2.2x on every element of this capture) — a real
question, and a different one.

## Acceptance Test

`tests/unit/test_the_width_comes_from_the_graph_not_the_argv.py`: on a
fixture where `graph.json` resolves an element to 8 and its recipe
writes `make -j2`, the ratio divides by 8, both numbers are published,
and the field naming the denominator says `graph`. On `core.bst`
(`notparallel`, peak 2) the ratio is not 2.0 and the overlap is a
finding. On an element that runs neither make nor ninja, the recipe
request is absent and the ratio is still computed.

**Mutations** (`falsify`):

1. Swap the denominator back to `requested_jobs`. `core.bst` returns to
   2.0. Catches the regex still driving the ratio.
2. Read `notparallel` as a missing width. The element's ratio appears
   where it should be absent. Catches a declared one read as unknown.
3. Delete the recipe's `-j` from the argv. The ratio is unchanged and
   only the recipe request goes absent. Catches the two fields collapsed
   back into one.

## Outcome (round 132, 2026-09-20) — 🟢 Done

**Premise:** held. `core.bst` is `notparallel`, ran two overlapping work
processes, and scored 2.0 against a width of one.

### The gap, measured

```text
core.bst     graph.max_jobs=1   notparallel=True  regex=1   peak=2   achieved_vs_requested=2.0
codegen.bst  graph.max_jobs=4   notparallel=None  regex=4   peak=4   achieved_vs_requested=1.0
```

The denominator was `-j(\d+)` over the argv of `make`, `gmake` and
`ninja`, highest wins. It is right wherever the recipe writes the
number the element resolved to — every element of this fixture — and
silently absent or wrong wherever it does not.

### After

```text
core.bst     graph=1   recipe=1    denominator=graph  findings=['pinned_to_one_job', 'overlap_exceeds_granted_width']
codegen.bst  graph=4   recipe=4    denominator=graph  findings=[]
```

Two numbers that can disagree are two fields: `resolved_jobs` from
`graph.json` (`notparallel` is a width of one, not a missing value),
`requested_jobs` still the recipe's own request, and
`jobs_denominator` naming which the ratio divided by. Overlap the
element was never granted is a finding about the sandbox, so the ratio
is held at 1.0 and `overlap_exceeds_granted_width` carries the fact.
An element with no resolved width gets no ratio; an element that ran
neither make nor ninja still gets one.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| B1 | `notparallel` read as a plain `max_jobs` | `test_notparallel_is_a_width_of_one_and_not_a_missing_value` (1) |
| B2 | the denominator swapped back to `requested_jobs` | `test_the_graph_wins_where_the_two_disagree` (1) |
| B3 | the two fields collapsed back into one | the same clause (1) |
| B4 | a missing width read as one | `test_no_resolved_width_is_no_ratio` (1) |
| B5 | the ungranted overlap not reported | `test_notparallel_is_a_width_of_one...` (1) |
| B6 | the ratio gated on a recipe request again | `test_an_element_running_neither_make_nor_ninja_still_scores` (1) |

The disagreement case has no committed fixture — every element of
`macro_micro` agrees, which is why the regex survived — so the guard
builds one: an element `graph.json` resolves to 8 whose recipe writes
`make -j2`.

### Deviation from the Required Fix

Mutation 1 as filed — swap the denominator back, `core.bst` returns to
2.0 — cannot discriminate on `core.bst`: both widths are 1 there, and
what moved its 2.0 is the overlap finding, not the divisor. B2 runs it
on the disagreement fixture, where the two give 0.5 and 2.0.

The join's two functions are in `bga/plane2.py`, not in the tracer the
Required Fix names: `graph.json` is written by `extract_run` **after**
the report, so the tracer cannot read it when it computes the ratio.
`_PerElementParallelism.finish()` therefore publishes no ratio at all
and the capture fills it the moment `extract_run` returns; the same
function runs at read time in `bga analyze`, so a capture taken before
this item stops dividing by the wrong number rather than waiting for a
re-capture. Dependency direction is tools → bga, so the shared
functions live on the bga side.

```text
make test: 8955 passed, 174 skipped, 1 warning in 329.80s (0:05:29)
make lint: All checks passed! / clean: 567 finding(s) match tests/quality_baseline.json
```
