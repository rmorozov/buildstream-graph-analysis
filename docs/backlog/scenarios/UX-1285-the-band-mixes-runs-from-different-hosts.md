# UX-1285: the band a review build is judged against mixes runs from different hosts

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-899, UX-186 | **Found by:** the 2026-10-02 state audit (`bga/run_store.py:245-253`), ahead of the owner's pilot | **Serves:** R4 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

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

## Outcome
