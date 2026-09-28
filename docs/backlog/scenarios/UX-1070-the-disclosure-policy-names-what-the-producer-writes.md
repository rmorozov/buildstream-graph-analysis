# UX-1070: the disclosure policy names what the producer writes

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1060 | **Found by:** a researcher checking #298's review findings (2026-09-28) | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** contracts | **Area:** bga | **Shape:** mechanical

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
classed per `docs/design/anonymized-bundle.md` §3: plane2's `schema`,
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
