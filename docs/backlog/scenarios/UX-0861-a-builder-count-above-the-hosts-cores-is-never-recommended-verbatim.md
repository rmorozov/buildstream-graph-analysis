# UX-861: a builder count above the host's cores is never recommended verbatim

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-116 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R5 (a recommendation the operator can apply as read) | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

`compute_capacity_recommendation` (`bga/correlate.py`) takes the
CPU constraint as `host_cores * builders / cores_busy` and binds on the
smallest of three; nothing clamps it. When the graph and memory
constraints allow more, the CPU figure decides alone, and the
repository's own fixture asserts it recommends 16 builders on an 8-core
host. `UX-116` bounded the *absent* constraint (never infinite); the
present one still names a builder count above the cores it sits beside.

## Required Fix

`bga/correlate.py`: a CPU-bound `recommended_builders` is clamped to
`host_cpu_count`, the constraint row records `clamped_from` (the
unclamped figure) and the finding's sentence says the host's cores
bound it; `bga/schemas.py` gains the key (additive).

## Decomposition

Input classes: CPU allows under, at and above the cores; the journey
it extends is R5's capacity question from `UX-116`.

## Out of Scope

A memory-bound or graph-bound figure above the cores, which the host
can hold; re-deriving the constraint from a peak rather than the average.

## Acceptance Test

`tests/unit/test_capacity_recommendation.py`: the fixture at
`cores_busy=2.0, host=8, builders=4` reads `allows 8` with
`clamped_from 16`; mutation: remove the clamp - red.

## Outcome — parts measured by the implementer track

**Premise:** held — the repository's own fixture did recommend a
builder count above the host's cores.

### The gap, measured

```text
$ git show ede1ce6f:tests/unit/test_capacity_recommendation.py | sed -n '82,94p'
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=2.0, host=8), _envelope(64), knee=64,
            builders=4, native_max_jobs=4,
        )
        cpu = next(c for c in recommendation['constraints'] if c['name'] == 'CPU')
        # 0.5 cores per element, 8 cores -> 16.
        assert cpu['allows'] == 16
```

At `host=8`, `cores_busy=2.0`, the CPU constraint allowed 16 - double
the host's own cores - with nothing clamping it.

### After

```text
$ python3 -m pytest tests/unit/test_capacity_recommendation.py -q -k \
    "test_the_cpu_ceiling_is_derived_from_the_measured_draw or \
     test_a_cpu_figure_under_the_cores_is_not_clamped or \
     test_a_clamped_cpu_figure_never_exceeds_the_host or \
     test_the_title_says_the_hosts_cores_bound_a_clamped_figure"
4 passed in 0.60s
```

The same fixture now reads `allows 8`, `clamped_from 16`. The finding's
sentence, on the motivating shape (`builders=16`, `host=8`):

```text
Capacity: builders 16 x max-jobs 16 on 8 core(s): CPU binds at 8 (the
host's cores bound it, not the raw 64), below the 16 configured - more
builders contend rather than overlap here
```

### Mutations verified red and reverted (1)

| # | mutation | reddened | count |
|---|---|---|---|
| A1 | `bga/correlate.py`: `clamped_from = None` unconditionally (clamp removed) | `test_the_cpu_ceiling_is_derived_from_the_measured_draw`, `test_a_clamped_cpu_figure_never_exceeds_the_host`, `test_the_title_says_the_hosts_cores_bound_a_clamped_figure` | 3 of 29 |

```text
$ python3 -m pytest tests/unit/test_capacity_recommendation.py -q
29 passed in 0.52s   (mutation reverted)
```

Deviation (merge): the verifier passed it and named the guide's
illustrative capacity block (`docs/guides/cli.md`, the 4-core example)
as wrong under the clamp - CPU now binds at 4, not the graph at 6 -
so the session rewrote that block at merge and named the clamp in the
sentence under it; the macro_micro export bound lands with `UX-864`'s
at 532,000 over their summed deltas.
