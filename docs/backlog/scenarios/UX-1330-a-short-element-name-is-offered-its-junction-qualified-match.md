# UX-1330: `whatif --element pkgs/gcc-libs.bst` is refused without offering the junction-qualified element it means

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1 | **Topic:** cli | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_short_element_name_is_offered_its_junction_qualified_match.py`

## Motivation

Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1.

```text
$ bga whatif --element pkgs/gcc-libs.bst
  Refused: Not in this run's graph: pkgs/gcc-libs.bst. A subset quietly missing a member projects a different question from the one asked.
```

The run holds `junctions/platform.bst:junctions/base.bst:pkgs/gcc-libs.bst`
(`bga/whatif.py:131`). Users type the name they see in their editor.

## Decomposition

Input classes: a short name matching one junctioned element; matching several (ambiguous); matching
none. Surfaces: `whatif --element`, `blast` with an element name.

## Required Fix

The refusal names the junction-qualified element(s) whose last component equals the name given,
as "did you mean"; it still refuses rather than substituting.

## Out of Scope

Fuzzy matching.

## Acceptance Test

On the stand-in, the refusal names `junctions/platform.bst:junctions/base.bst:pkgs/gcc-libs.bst`;
a guard asserts the one-match and the ambiguous case. Reading taken in this container.

## Outcome

**The gap measured.** `bga whatif --element pkgs/gcc-libs.bst <jproj run>` (run
`/root/walk/jproj/.bga/runs/20261003T135009Z/run`) before: `Refused: Not in this run's graph: pkgs/gcc-libs.bst. ...`
with no suggestion.

**The close measured.** After: `... Did you mean junctions/platform.bst:junctions/base.bst:pkgs/gcc-libs.bst?`
still `Refused`. `bga blast pkgs/gcc-libs.bst <run>` ends `Did you mean junctions/platform.bst:junctions/base.bst:pkgs/gcc-libs.bst?`.
Surfaces beyond the task's: `blast/v2` gains the additive `did_you_mean` array (`bga/schemas.py`,
`docs/guides/json-contracts.md` row, key count 626 -> 627). 100 passed across the new file, blast, whatif, contract and
document tests; the wider blast/whatif-naming sweep stopped at 1 failure, `test_the_context_map_is_the_tree`
(`tests/ci_reference.json`, `flake_ledger.json`, `touch_map.json` absent from this worktree; not this change).

**Mutation table.**

| Mutation | Reddened | Count |
|---|---|---|
| match whole uid, not last component | whatif one/several + blast fixture | 3 failed |
| drop `_suggestions` from the refusal | whatif one/several | 2 failed |
| keep only the first known uid | whatif tests | 2 failed |
| prefix match instead of last component | the longer-name test | 1 failed |
| `blast` payload key always `[]` | payload-from-fixture test | 1 failed |
| drop both blast text lines | blast text tests | 2 failed |

### Deviation from the Required Fix

The verifier held it: `did_you_mean` was a required key; made optional and always-written, folded. 84548195 then admits always-written keys in the blast emit guard; the surface is 628. (`fd4141f8`)
