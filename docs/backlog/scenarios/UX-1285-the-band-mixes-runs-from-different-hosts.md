# UX-1285: the band a review build is judged against mixes runs from different hosts

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-899, UX-186 | **Found by:** the 2026-10-02 state audit (`bga/run_store.py:245-253`), ahead of the owner's pilot | **Serves:** R4 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** test_the_band_is_drawn_on_the_candidates_host.py

## Motivation

`--band-from-class` selects the last N runs of the candidate's
`build_class` (`runs_of_class`, `bga/run_store.py:227`), and the
filter is `buildclass.same_class` alone. A review fleet with two
runner types puts both in the band. The pair check (`--allow-cross-host`,
`bga/cli.py:1339`) guards baseline against candidate, never the members.
A band drawn over two machines is wider than either machine's noise,
so a real regression on the fast runner reads as inside the band, and
a slow runner's candidate reads as a regression against a band led by
fast runs. `bga baseline` already warns on this (`_host_drift`,
`tools/bst_baseline_set.py:364`); the gate does not.

## Decomposition

Input classes: all members on the candidate's host; members split
across two `cpu_model`s; members with no host manifest (pre-UX-186);
candidate with no host manifest; `--allow-cross-host` passed. Journey:
`bga compare BASE CAND --band-from-class --fail-on-regression`.

## Required Fix

Band members are selected by class *and* host: a member whose
`hostinfo.differing_fields` against the candidate is non-empty is
skipped, unless `--allow-cross-host` is passed. A member or candidate
with no manifest is kept, as `classify` treats `unknown` today. The
refusal (exit 8) and the comment name how many runs were skipped for
host, so "too few runs" is never silent about why.

## Out of Scope

A fuzzy host class (memory within a tolerance); grouping a fleet by
runner label. If exact `memory_bytes` splits a real fleet, that is a
pilot finding for its own row.

## Acceptance Test

A store of six same-class runs, three per `cpu_model`: the candidate
on host A gets a band of the three A runs; with `--allow-cross-host`,
five. Two A runs and four B runs: exit 8, naming four skipped for host.

## Outcome (2026-10-02)

**Premise:** held — the base pooled both hosts.

### The gap, measured

`repro1285.py` stores (the guard's `_store`, `golden/mixed_task_kinds`
runs, host manifests `Xeon A`/`EPYC B`), `bga compare … --band-from-class`
on the base tree `1448af2c7`:

```text
six runs, 3 A + 3 B, baseline the newest B, candidate A, ci-comment:
band from baseline 5 runs, widened to the fixed 1% rule: 99.
two A + four B, baseline and candidate A, --fail-on-regression:
  Judged against a noise band from baseline 6 runs: 99.01s .. 101.01s - widened to the fix
exit=0
```

### The close, measured

The same stores, this branch:

```text
band from baseline 3 runs, widened to the fixed 1% rule: 99.0s .. 101.0s — from `20260903T000000Z`, `20260902T000000Z`, `20260901T000000Z` — 2 runs of this class skipped, measured on another host
exit=0
--allow-cross-host:
band from baseline 5 runs, widened to the fixed 1% rule: 99.0s .. 101.0s — from `20260905T000000Z`, … `20260901T000000Z`
exit=0
two A + four B:
Band gate REFUSED: … this store holds other 2 runs of that class within the last 10 on its host (4 skipped for host: cpu_model; pass --allow-cross-host to pool them), below the 3 a measured band needs. …
exit=8
```

### Mutations verified red and reverted (5)

`test_the_band_is_drawn_on_the_candidates_host.py`, 5 tests:

| # | mutation | reddened |
|---|---|---|
| M1 | `runs_of_class` ignores the host | three-A band, refusal, no-manifest member: 3 failed |
| M2 | `--allow-cross-host` not read | the five, 1 failed |
| M3 | the refusal drops the skipped count | the refusal, 1 failed |
| M4 | `_band_selection` always empty | three-A band, no-manifest member: 2 failed |
| M5 | a member with no manifest skipped | the no-manifest member, 1 failed |

The candidate-without-manifest test is not separately mutable here:
`hostinfo.differing_fields` returns `[]` for a `None` side, and that is
`classify`'s rule, not this row's.
