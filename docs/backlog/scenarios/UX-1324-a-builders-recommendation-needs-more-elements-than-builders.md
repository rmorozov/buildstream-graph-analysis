# UX-1324: A run that rebuilt one element recommends `--builders 1` because memory binds, while saying memory fits 15.7 GB

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1, R5 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1. On the incremental snapshot that rebuilt only `apps/browser.bst`:

```text
  1 builder: memory binds — below the 4 configured
    -> Lower --builders to 1.
    memory allows 1: the 1-builder envelope fits in 15.7 GB (measured over 1 element peak, so it says nothing above 1)
    The sweep itself checked memory too: memory-bound at 8.
```

The finding is built in `bga/findings.py:1300-1380`.

## Decomposition

Input classes: a cold run with more elements than builders (today's advice stays); an incremental
run that built fewer elements than the configured builders; a run whose memory envelope is
measured over n peaks with n below the configured builders. Surfaces: Key Findings, `correlate`'s
capacity line, the page's capacity recommendation.

## Required Fix

A memory bound measured over n element peaks never binds below n builders' worth of headroom it
did not measure: when the run built fewer elements than the configured builders, the builders
recommendation is withheld with one line saying why (too few elements to measure a bound).

## Out of Scope

The sweep's own model.

## Acceptance Test

On the stand-in's one-element incremental run, no "Lower --builders" line appears and the withheld
line does; a guard over a fixture with one built element asserts it. Reading taken in this container.

## Outcome
