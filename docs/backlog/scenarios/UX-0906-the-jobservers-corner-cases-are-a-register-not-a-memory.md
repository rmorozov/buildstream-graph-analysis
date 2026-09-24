# UX-906: the jobserver's corner cases live in twelve task files and no register

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-841..UX-852, UX-878, UX-884, UX-888 | **Found by:** the 2026-09-20 rollout thread — the owner asks which corner cases the integration has to survive, and answering it meant reading twelve closed task files | **Serves:** R2 (whose recipe is the corner case), R5 and R4 (who need to know what the mode does not cover before switching it on) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** mechanical

## Motivation

What the injected jobserver has to survive is real knowledge this
repository has paid for — a GCC LTO ICE (`UX-878`), a `make` policy
whose exclusion is unproven (`UX-884`), a ninja wrapper that had to own
ninja's `-j` (`UX-888`), a pin rule that must never force `-j1`
(`UX-842`), a minimal sandbox that broke on a shim needing `dirname`
(round 126) — and it lives scattered across twelve task files and two
rounds. Nobody can answer "what breaks under this mode" without reading
all of them, which is the question the owner asked and the question
every adopter asks first.

The list in section 7a of
[`continuous-build-improvement.md`](../../design/continuous-build-improvement.md)
is this round's attempt at it, written from the tree. It is a
brainstorm, not a measurement: some rows have a guard and a closed task
behind them, several have neither.

## Required Fix

Turn that list into a register with a column that says, per corner case,
which of three states it is in: **guarded** (a test or an example
fails when the mode breaks it), **known and unguarded** (a task file
names it, nothing fails), or **unexamined** (this round wrote it down
from reasoning, and no capture has met it). Each guarded row names its
guard; each unexamined row is a candidate filing rather than a claim.

The register is derived where it can be — the policy table in the shim
is code, and the closed rows are files — rather than a list that drifts
from both.

## Decomposition

surfaces: the design document's section 7a, the jobserver's policy table in `tools/native_trace/bwrap_shim.py`, and a guard that reads both
guards: a test that every policy the shim implements appears in the register, and every register row claiming a guard names one that exists
gap: the unexamined rows cannot be resolved by reading — each needs a capture that meets the case, which is why they are candidates and not findings
track: `implementer` for the derived half; the states are the session's to judge
gate: with `UX-905`, which will meet several of these rows on a real project

## Out of Scope

Fixing any corner case the register finds unguarded — each one is its
own row, filed when the register says which. Corner cases of the capture
that are not about the jobserver.

## Acceptance Test

The register lists every policy the shim implements, each row carries
one of the three states, every "guarded" row names a guard that exists,
and a guard reddens when a policy is added to the shim without a row.
Mutations: add a policy to the shim (the guard names the missing row),
point a row at a guard that does not exist (red), change a state word to
one not in the three (red).

## Decision

The `architect`, round 141, at `ad27b616`.

```text
Route:     section 7a's table becomes the register in place, with three columns added:
           `policy` (the shim policy names the row covers, or -), `state` (exactly one
           of guarded | known-unguarded | unexamined) and `evidence` (a tests/unit/test_*.py
           or examples/ path for guarded, a UX-NNN for known-unguarded, - for unexamined);
           rows added so every policy has one (today's table lacks ninja_static, jobs_env,
           unknown_kind, cmake_meson, ninja_client). A new guard derives the policy set
           from the shim's ast - the third element of every `return` tuple in
           kind_job_env/_ninja_aware_env, each `base_policy` literal, module constants
           resolved - and reads the table under the "## 7a." heading. The states are
           the session's call at merge; the implementer proposes them from the tree
Rejected:  a JOBSERVER_POLICIES set declared in the shim - a new `return ..., "go"` could
           skip it; the ast reads what the code returns
           a separate register file - the task names section 7a, and a second list drifts
           enumerating kind_job_env over known kinds - a new kind branch is never called
Files:     docs/design/continuous-build-improvement.md (section 7a only, lines 188-218; no
           other section); tests/unit/test_every_jobserver_policy_has_a_register_row.py.
           Reads, never edits: tools/native_trace/bwrap_shim.py
Guard:     test_every_jobserver_policy_has_a_register_row.py: every derived policy appears in
           some row's `policy` cell; every state cell is one of the three words; every
           guarded row's evidence path exists; every known-unguarded row's UX id has a file
           under docs/backlog/scenarios/; an unexamined row carries no evidence
Mutation:  add `if kind == "go": return [], [], "go"` to kind_job_env (red, names `go`);
           point a guarded row at tests/unit/test_no_such_guard.py (red); change a state
           to `partial` (red); give a known-unguarded row UX-99999 (red)
Class:     product - the adopter's "what breaks under this mode" (R2, R4, R5)
Split:     one track; parallel with UX-901, which does not touch bwrap_shim.py or section 7a
Question:  none
```

## Outcome

Gap measured: before, section 7a's table had 3 columns, 13 rows, no
`policy`/`state`/`evidence` and 0/8 of the shim's own `kind_job_env`/
`_ninja_aware_env` policies named anywhere. After: 18 rows (5 added for
the missing policies), 8/8 policies named, 10 `guarded`, 1
`known-unguarded` (`UX-884`), 7 `unexamined`.

Close measured (`python3 -m pytest tests/unit/test_every_jobserver_policy_has_a_register_row.py -q`):
`5 passed in 0.09s`. `make test-touching`: `1 failed, 1625 passed, 3
skipped` — the one failure (`test_every_module_is_on_the_map` wanting
`tools/jobserver_arms.py` on the context map) predates this track,
from `UX-901`'s merge at `68305095`, and neither file it names is one
this task touches.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| add `if kind == "go": return [], [], "go"` to `kind_job_env` | `test_every_derived_policy_appears_in_some_row` | 1 failed, 4 passed |
| point the ninja row's evidence at `test_no_such_guard.py` | `test_every_guarded_rows_evidence_path_exists` | 1 failed, 4 passed |
| change the cargo row's state to `partial` | `test_every_state_cell_is_one_of_the_three_words` | 1 failed, 4 passed |
| give the GCC LTO row `UX-99999` | `test_every_known_unguarded_rows_ux_id_has_a_task_file` | 1 failed, 4 passed |

Each reverted; `5 passed in 0.09s` restored after every one.
