# UX-684: the cached-build verdict — does the graph rebuild the cheapest subgraph?

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-682 (expected rebuild cost), UX-477 (the cold verdict's rule) | **Serves:** R3 showing evidence, R8 reading it | **Topic:** analysis | **Shape:** judgement

## Motivation

The cold build has a verdict — chain-bound / scheduler-bound /
inconclusive (`bga/findings.py:1610-1637`), with the floors and the
sweep behind it. The cached build, which is most builds, has none:
the graph owner cannot say whether the shape lets the likely changes
rebuild little, and the tool's blast findings speak of one resource
at a time.

## Required Fix

A `cached_shape` verdict from `UX-682`'s distribution: the share of
the change history whose rebuild stayed under the p50 weighted blast
("most changes rebuild the cheapest subgraph"), the elements whose
changes dominate the expected cost, and height versus weight stated
separately — stack and other assembling elements add height for
free, a single heavy element adds weight — so "split the tall chain"
and "isolate the heavy element" are two different advices. The
verdict's rule and its denominator are stated the way `UX-477` states
the cold one's.

## Out of Scope

- Simulating a proposed split — `UX-230`'s what-if prices fixes to
  durations; pricing a graph edit is its own model, filed when the
  verdict has a consumer.

## Acceptance Test

Example 06's history: the verdict names the share of changes under
the p50 blast and the dominant element; mutation: weigh by count
instead of duration — red.

## Outcome

**Gap measured:** `git show d3e78b8a:bga/correlate.py | grep -c
cached_shape` → `0`; no `cached_shape` key, function or verdict
constant existed anywhere in the package.

**Close measured:** Example 06 carries no captured kept-log tree, so
this runs against the checked-in capture of the same project,
`tests/fixtures/macro_micro`, and a real log tree built the way
`UX-682`'s own tests build one. Reproduces exactly:

```python
# python3 - <<'PY' (writes /tmp/ux684-logs)
from pathlib import Path
from datetime import datetime, timedelta, timezone
root, base = Path("/tmp/ux684-logs"), datetime(2026, 8, 1, tzinfo=timezone.utc)
def write(element, n, hour_step):
    d = root / "macro-micro" / element.removesuffix(".bst")
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        dt = base + timedelta(hours=hour_step * i)
        (d / f"{i+1:08x}-build.{dt:%Y%m%d-%H%M%S}.log").write_text(
            f"BuildStream 2.7.0 - Someday, {dt:%d-%m-%Y} at {dt:%H:%M:%S}\n"
            f"[--:--:--] START   [{i+1:08x}] {element}: Build\n"
            f"[--:--:--] START   {element}: Running commands\n"
            f"[00:00:01] SUCCESS {element}: Running commands\n"
            f"[00:00:01] SUCCESS [{i+1:08x}] {element}: Build\n")
write("lib-f.bst", 3, 2); write("lib-d.bst", 5, 2); write("lib-b.bst", 2, 5)
write("lib-a.bst", 3, 5); write("toolchain.bst", 2, 9)
```

```text
$ PYTHONPATH=. python3 -m bga.cli cache-logs /tmp/ux684-logs --format json > /tmp/cl.json
$ PYTHONPATH=. python3 -m bga.cli correlate tests/fixtures/macro_micro/run \
    tests/fixtures/macro_micro/plane2.json --cache-logs /tmp/cl.json --format json
"cached_shape": {"verdict": "rebuilds_the_cheapest_subgraph",
  "cheap_share": 0.5333333333333333, "cheap_changes": 8, "total_changes": 15,
  "p50_weighted_blast_us": 14150000,
  "dominant": [{"element": "lib-a.bst", "expected_cost_us": 63450000,
    "share_of_expected_cost": 0.4017, "height": 7, "weight_us": 21150000,
    "height_rank": 1, "weight_rank": 1, "advice": "isolate the heavy element",
    "assembling_kind": false}, ...],
  "sentence": "8 of 15 recorded changes (53%) rebuilt at or under the graph's
    own median weighted blast. lib-a.bst dominates the expected cost at 40%,
    also the tallest: 7 element(s) below it, 21.1s of its own weight;
    isolate the heavy element."}
```

Real macro_micro is one straight dependency chain, so height and
weight agree for every element and every advice ties (`isolate`)
here; the guard below adds a private synthetic chain to exercise
`split`.

The four test files naming this: `53 passed`. `make test-touching`:
`3379 passed, 41 skipped`, one red pre-existing on the base (Direction
19's cadence, fixed on the branch). ruff, `dev_baseline.py --check`,
pymarkdown clean.

**Mutation table** (each: copy saved, mutated, `pytest
tests/unit/test_cached_shape_ranks_dominant_by_duration_not_count.py
-q`, restored from the copy, re-run green):

| mutation | reddened | count |
|---|---|---|
| `_dominant_elements` ranks by `rebuilds` instead of `expected_cost_us` | `test_dominant_is_ranked_by_duration_weighted_cost_not_change_count`, `test_the_advice_matches_an_independent_height_and_weight_rank_comparison` | 2 failed, 1 passed |
| `cached_shape`'s p50 taken over the recorded-change elements instead of over the whole graph | `test_cheap_share_matches_an_independent_recount` | 1 failed, 2 passed |
| `_height_vs_weight_advice`'s two branches swapped | `test_the_advice_matches_an_independent_height_and_weight_rank_comparison` | 1 failed, 2 passed |

All three restored to `3 passed`.

**Deviation.** `cached_shape` is a top-level `correlate` key, not a
`findings[]` id: it needs Plane 3, which `analyze` never reads. One
verifier HOLD — the log tree had no command, the advice branch no guard
(a swap left 52 green); fixed: the script pasted, a third guard on a
synthetic chain, the tie ruled "isolate the heavy element, also the
tallest". Two commits, one verifier (HOLD, then PASS).
