# UX-1324: A run that rebuilt one element recommends `--builders 1` because memory binds, while saying memory fits 15.7 GB

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1, R5 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_builders_recommendation_needs_more_elements_than_builders.py`

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

**Gap measured** (`bga analyze /root/walk/jproj/.bga/runs/20261003T135218Z/run`, at `2725b2b1`; `cache.built_elements` 2, `--builders` 4):

```text
  1 builder: memory binds — below the 4 configured
    -> Lower --builders to 1.
    memory allows 1: the 1-builder envelope fits in 15.7 GB (measured over 1 element peak, so it says nothing above 1)
```

**Close measured** (same run, this container; `grep -c "Lower --builders"` prints 0):

```text
  2 elements built, too few to bound 4 builders: builders recommendation withheld
```

`--format json`: `capacity_recommendation.verdict` "Builders recommendation withheld: this run built 2 elements, too few to measure a bound for 4 builders.", `withheld: {built_elements: 2, reason}`, `recommended_builders`/`binding_constraint`/`builders_change` null, `constraints` empty; `agent_sizing.builders.recommended` null; the finding's step is `why_none`. The cold run `135009Z` still reads `3 builders: graph binds`. The count is `cache.built_elements` (the Pipeline Summary's build `processed`); absent, nothing is withheld. `withheld` is a permitted key (surface 626 -> 627 keys in `json-contracts.md`), no schema bump.

**Mutation table** (`python3 -m pytest -n 1 -q tests/unit/test_a_builders_recommendation_needs_more_elements_than_builders.py`, 5 tests):

| mutation | reddened | count |
|---|---|---|
| never withhold (`< builders` -> `< 0`) | unit, text, json | 3 failed, 2 passed |
| boundary `<` -> `<=` | as many built as builders still recommends | 1 failed, 4 passed |
| `cli` passes `built_elements=None` | text, json | 2 failed, 3 passed |
| finding ignores `withheld` | text, json | 2 failed, 3 passed |

Reverted from copies; 5 passed.

### Deviation from the Required Fix

Rule: `built_elements < builders` withholds the recommendation; no count withholds nothing. The merged tree reddened `test_no_schema_description_names_a_key` on `withheld`'s prose; reworded in a fixup, autosquashed. (`793c3f02`)
