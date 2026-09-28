# UX-1063: analysis commutes with anonymization

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1062 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), sections 6.4 and 6.10; the owner's review on #298, finding 5, and its follow-up at `8c3bead1`, finding 2: a release criterion for UX-1062's export | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** guards | **Area:** bga | **Shape:** mechanical

## Motivation

An outside reader diagnoses the anonymized analysis; if it differs from
the real one beyond names, the diagnosis is of a different build. Any
output sorted or tie-broken by name reorders under HMAC pseudonyms.

## Required Fix

On the golden fixtures, `analyze(anon(capture))` and
`anon(analyze(capture))` agree on every invariant measurement exactly;
where a choice is tied, they agree on the set of equally valid choices,
not the representative; display order is not compared. Name-dependent
tie-breaks found in `bga/` are replaced where a name-independent order
exists; findings with no such order are listed by name in the guard.

## Out of Scope

Order-preserving pseudonyms: rejected, they break when an element is
added.

## Acceptance Test

`tests/unit/test_analysis_commutes_with_anonymization.py` over every
golden fixture. Mutation: reintroduce a sort by uid on the critical
path's tie-break, and it reds.

## Decision

Route:     the guard runs analyze(anon(x)) and anon(analyze(x)) under a fixed test key and compares in three tiers: (1) every measurement exactly (ints; floats isclose rel 1e-12; absolute times through the export's epoch shift; class-A strings and `uid|` task-key prefixes through the UX-1061 map); (2) outputs where a name tie-break truncates a list or picks a representative are re-keyed on graph.json position (`element_order(graph)`), which survives anonymization because UX-1062 rewrites in place and nothing in bga/ingest or bga/normalize sorts - these compare exactly, representative included; (3) the Listed outputs compare as sets.
Rejected:  set comparison everywhere (the named mutation could not redden it); order-preserving pseudonyms (out of scope, break on an added element); the golden fixture alone (`mixed_task_kinds` is one chain, no tie).
Files:     bga/graph/edg.py (`element_order` helper) · bga/graph/fan_in.py:64,97 · bga/structural/analyzer.py:843,848 · bga/structural/consolidation.py:65 · bga/diagnostics/analyzer.py:118,124 · bga/findings.py:1784,1845,1852 · bga/correlate.py:2476 · tests/unit/test_analysis_commutes_with_anonymization.py
Kept:      fan_in.py:47 (dominator sets nest); structural/analyzer.py:313 (choke points comparable); edg.py compute_critical_path, horizon 813-833, latent heavies 879 already break ties by document order.
Listed:    attribution / blame chain (blame_chain.py:469,1462 smallest task key, required by spec §7.1/§36.4, spec editable only inside Part 32); sources.py:414; display-only sorts (blast.py:308-314, 346-358 per depth; sources.py:333-357; structural levels analyzer.py:379; consolidation `elements`; envelope.py:111-135; every uid-keyed dict); prose (class F) not compared.
Guard:     tests/unit/test_analysis_commutes_with_anonymization.py over tests/fixtures/golden/* plus topologies.diamond() and topologies.shared_base_wide() via write_run_dir; preconditions first: anonymization kept graph.json element order, and the test key's HMAC order of each tied pair differs from its name order.
Mutation:  compute_critical_path `successors.get(current, [])` -> `sorted(...)`, diamond reds; uid back as the tie key at fan_in.py:97, shared_base_wide reds (6 dependents tied at 1, TOP_FAN_IN 5).
Class:     product
Split:     one track after UX-1062, model opus (>150 lines, UX-1039).

## Outcome
