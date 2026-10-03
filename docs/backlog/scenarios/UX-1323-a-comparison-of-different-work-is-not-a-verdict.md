# UX-1323: `compare` calls two incremental runs that rebuilt different elements IMPROVED, and the cold-then-incremental refusal names no next step

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1, R4 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_comparison_of_different_work_is_not_a_verdict.py`

## Motivation

Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1. The README's loop (snapshot, change, snapshot):

```text
# snapshot 2 (cold -> incremental)
Refusing to compare these runs (run_mode):
Pass --allow-mismatch to compare anyway ...
# snapshot 3 (rebuilt apps/browser.bst) vs snapshot 4 (rebuilt apps/shell.bst)
Verdict: IMPROVED  (total duration -5.36s, -56.3%, 9.51s -> 4.15s)
  Why: ... No element present in both runs shrank, so what moved is in the elements this change
  added or removed.
  apps/browser.bst: disappeared (6.30s, no delta to compare)
  apps/shell.bst: appeared (1.20s, no delta to compare)
```

The sentence is at `bga/compare.py:900`. In a developer's loop every edit rebuilds a different set.

## Decomposition

Input classes: same element set (today's verdict stays); disjoint built sets; overlapping sets
where the common elements moved; overlapping where they did not; cold vs incremental (refusal).
Surfaces: `bga compare` text and json, `bga snapshot`'s automatic compare, the CI comment, exit codes.

## Required Fix

When the two runs built different element sets and no element common to both moved
significantly, the verdict is a distinct `different work` state, not improved or regressed, with
its own line saying which elements each run built; exit code unchanged from no-change. The
cold-vs-incremental refusal names what to do: the next snapshot compares incremental against
incremental, and a fresh cache directory gives the project-wide picture.

## Out of Scope

A per-element noise band.

## Acceptance Test

On the stand-in, the browser-then-shell pair reads `different work`, and a guard over two fixture
runs with disjoint built sets asserts it in text and json. Reading taken in this container.

## Outcome

**Gap measured** (`bga compare 20261003T135218Z/run 20261003T135337Z/run` on `/root/walk/jproj/.bga/runs`, at `44afd957`):

```text
Verdict: IMPROVED  (total duration -5.36s, -56.3%, 9.51s -> 4.15s)
  Why: ... - so improved. No element present in both runs shrank, so what moved is in the elements this change added or removed.
```

The cold-vs-incremental refusal (`135009Z` vs `135218Z`) printed the check and `--allow-mismatch`, no next step.

**Close measured** (same pair, this container, exit 0):

```text
Verdict: DIFFERENT WORK
  The two runs built different elements: only the baseline built apps/browser.bst; only the candidate built apps/shell.bst
  Not a verdict, for reference only: total duration -5.36s, -56.3%, 9.51s -> 4.15s
```

`--format json`: `"verdict": "different work"`, `"verdict_kind": "different_work"`; `--format ci-comment` heads `**DIFFERENT WORK**` with the same line. The refusal now adds `Next: the next snapshot compares incremental against incremental; for the project-wide picture, capture with a fresh cache: XDG_CACHE_HOME=$(mktemp -d) bga snapshot -- bst build <target>`. The rule: built sets differ and the common elements' summed |delta| is inside the run's own band (fixed 1% or the baseline band); `different_work` joins `VERDICT_KINDS` (an added enum value, no schema bump - json-contracts.md's rule), marker `square`. `--fail-on-regression` is unchanged; `--band-from-class`'s gate keeps its direction on a `different_work` pair.

**Mutation table** (`python3 -m pytest -n 1 -q tests/unit/test_a_comparison_of_different_work_is_not_a_verdict.py`, 9 tests; counts below the first eight rows are from the 7-test run):

| mutation | reddened | count |
|---|---|---|
| `_is_different_work` always False | text, ci-comment, json | 3 failed, 4 passed |
| drop the built-set equality check | same built set keeps its verdict | 1 failed, 6 passed |
| common elements' moved sum forced to 0 | common element that moved keeps its verdict | 1 failed, 6 passed |
| band gate's different_work branch removed | band gate still fails a slower pair | 1 failed, 6 passed |
| refusal's `Next:` print removed | refusal says what to run | 1 failed, 6 passed |
| text's different-work line removed | text | 1 failed, 6 passed |
| ci-comment's line removed | ci-comment | 1 failed, 6 passed |
| common rows inherit the run kind | json rows | 1 failed, 6 passed |
| summed abs(delta) -> abs of the signed sum (verifier's survivor) | common +0.5 s/-0.5 s pair keeps improved | 1 failed, 8 passed |
| duration gate returns False on different_work | `--fail-on-regression` exits 4; band gate | 2 failed, 7 passed |

Reverted from copies; 9 passed.
