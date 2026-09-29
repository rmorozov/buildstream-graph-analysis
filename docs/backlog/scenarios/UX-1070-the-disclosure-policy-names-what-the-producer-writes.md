# UX-1070: the disclosure policy names what the producer writes

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1060 | **Found by:** a researcher checking #298's review findings (2026-09-28) | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** contracts | **Area:** bga | **Shape:** mechanical

**Guard:** test_the_disclosure_policy_names_what_the_producer_writes.py

## Motivation

A `plane2.json` from the current producer (compiled hook and spine, a
`dd` workload) returns 9 gaps from `disclosure.gaps`, so every real
capture refuses the anonymized export. The policy guard walks
`tests/fixtures/`, which predate `schema`, `resource_pressure`,
`process_outcomes`, `redundant_operations_coverage`'s counters,
`per_element_parallelism[]`'s job fields and run-context's
`jobserver_env`: the guard is fixture-shaped, not producer-shaped.

## Required Fix

Name every path the current producers write in `bga/disclosure.py`,
classed per `docs/design/anonymized-bundle.md` section 3: plane2's `schema`,
`resource_pressure`, `process_outcomes`, `commands_not_observed`,
`opens_captured.{A}.relative`/`dirfd`, `per_element_parallelism[]
.resolved_jobs`/`jobs_denominator`, `redundant_operations_coverage`'s
four counters; run-context's `jobserver_env`, `jobserver`,
`cpu_budget`, `memory_budget_mb`, `estimated_job_memory_mb`,
`build_class`, `artifact_weights`, `project_refs_provenance`,
`build_outcome.suspended`. Anything that can carry a secret
(`jobserver.auth`) is class G.

## Out of Scope

Streaming (UX-1069); command-line credentials (UX-1068).

## Acceptance Test

`tests/unit/test_the_disclosure_policy_names_what_the_producer_writes.py`:
compile the hook and spine, run a small workload, `summarize` it, and
assert `disclosure.gaps` is empty for plane2; build run-context
through its producer functions with every optional flag set and
assert no gaps. Skips, by UX-213's rule, where `cc` is absent.
Mutation: remove `resource_pressure` from the policy, and it reds.

## Outcome

**Gap measured.** `disclosure.gaps("plane2.json", "plane2/v3", [report])`
on a real hook+spine capture (`dd` workload, `--project-dir` set, one
element naming an unrun binary): **10** gaps before this fix - `schema`,
`resource_pressure`, `process_outcomes`, `commands_not_observed`,
`per_element_parallelism[].resolved_jobs`/`.jobs_denominator`,
`redundant_operations_coverage`'s `findings_cap`/`omitted_beyond_cap`/
`total_findings`/`display_floor_seconds` (one more than the Motivation's
9, from this run's extra `redundant_operations_coverage` counter).

**Close measured.** Same capture, same call, after: **0** gaps for
`plane2/v3`. A second document, run-context built through
`add_cpu_capacity_fields`, `add_memory_capacity_fields`,
`add_build_class`, `_read_bga_jobserver_env`, `artifact_weight
.weigh_elements` and `suspend.slept` with every optional flag set:
**0** gaps for `run-context/v9`.

**Mutation table.**

| Mutation | Reddens | Count |
|---|---|---|
| remove `resource_pressure.*` from `plane2/v3` | `test_a_real_plane2_report_has_no_disclosure_gaps` | 1 gap: `resource_pressure: not named by the policy` |
| revert `_Anonymizer._rename`'s F/G sentinel to `str(self._leaf(...))` | `test_a_class_f_or_g_map_key_drops_the_whole_entry` | `{'foo': {'None': 6}}` != `{'foo': {}}` |
| drop `_key_refused`'s class-C integer check | `test_a_class_c_map_key_that_is_not_a_number_is_a_gap` | `[]` != 1 gap on a non-numeric `killed_by_signal` key |

`opens_captured.{A}.relative`/`.dirfd` classed C (counts, `UX-865`);
`per_element_parallelism[].resolved_jobs`/`.jobs_denominator` classed C
(filled later by `apply_resolved_widths`, `None` until then);
`commands_not_observed`'s `named`/`observed`/`named_not_observed`
classed `B:binary` (basenames), `elements_with_gap[]` classed A;
`process_outcomes.killed_by_signal`/`.statuses` map keys classed C, now
enforced: `disclosure._key_refused` refuses a class-C key that is not
an integer-like string (verifier defect b - a secret string was
otherwise a valid key). `jobserver.mode`/`.auth` classed
`B:jobserver_mode`/`B:jobserver_auth` (closed vocab `{fd, fifo}`,
fail-closed) - the Required Fix's `G` for `auth` was written before the
producer was read: `jobserver_auth_style` (`tools/jobserver/ledger.py`)
and `run_traced_build`'s own docstring show it only ever holds the
style word, never a real fd/fifo string. `jobserver_env[].name`/
`.prefix` classed F (declared, unenumerated). `build_class.type`/
`.variant.{A}` classed A, not F (verifier defect a - the owner's
type-x-variant comparison class must survive sharing as stable
pseudonyms, and an F-classed map key rendered as the literal key
`"None"`, `bga/bundle.py`'s `_rename` calling `str(None)`); `_rename`
now returns a sentinel dropping the whole entry on any F/G-classed key.
`artifact_weights`' `cachedir`/`project` classed A, `source` classed
`B:artifact_weight_source` (`cas_walk`/`ref_absent`/`incomplete`/
`budget_exceeded`); `project_refs_provenance.sha256` classed E,
`.path` classed A; `build_outcome.suspended.suspended_seconds` classed C.

**At close:** `jobserver.auth` classed B `{fd, fifo}`; `build_class`
type/variant A; an F/G map key drops the entry; a C map key must be
integer-like or the gap check refuses; policy gap 10 before, 0 after.
