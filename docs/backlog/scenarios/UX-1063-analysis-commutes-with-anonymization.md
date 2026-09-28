# UX-1063: analysis commutes with anonymization

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1062 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), sections 6.4 and 6.10; the owner's review on #298, finding 5, and its follow-up at `8c3bead1`, finding 2: a release criterion for UX-1062's export | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** guards | **Area:** bga | **Shape:** mechanical

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

**Gap measured** at `7bd141a2`: the guard below, run against that base's
`bga/` (`/tmp/<track>/swap.sh base`): `3 failed, 10 passed`. Golden
`mixed_task_kinds` green (one chain, no tie); `diamond` red on
`serial_chains[].best_split`, `top_fan_in`, the fan-in finding's
`elements`; `shared_base_wide` red on `top_fan_in[0..4]`; `fan_in` red
on `serial_chains[].members[0]`, `top_blast_radius[1..2]`.

**Close measured.** `edg.element_order(graph)`, the uid's graph.json
position, replaces the name as tie key at `fan_in.py` (`top_fan_in`;
`direct` now *selects* its 40 by position, still shown by name),
`structural/analyzer.py` (best split, chain rank),
`consolidation.py`, `diagnostics/analyzer.py` (`order_blast_radius`
takes `order`; the uid stays last, for a uid outside the graph),
`findings.py:1784,1845,1852` and `correlate.py:2476`. Those two see no
graph: `compute_fan_in` now emits its rows in graph.json order and they
read that order off `fan_in`. `python -m pytest -q
tests/unit/test_analysis_commutes_with_anonymization.py`:
`13 passed in 1.57s` - golden, `diamond`, `shared_base_wide`, plus
`fan_in` (4 tied predecessors, which reaches the chain rank and the
blast ranking), topologies moved to a 2026 epoch so the export's shift
is `1790000000000000` and not 0.

Two existing outputs moved, refreshed with `dev_refresh_analysis.py
--write`: `golden/.../expected_output.json` (`elements.fan_in` key
order only) and `with_timeline/analyze.json` (the same, plus
`bottleneck.serial_chains[]`, tied chains now in graph order).
`test_the_ranking_orders_equals.py`'s source grep now reads the call
with its third argument.

Found: the export shifts the wall origin to 0, and `_run_instance`
reads a 0 start as none, so `run_instance.started_at` and every
`copy_text`'s `Captured:` line vanish from an anonymized analysis. The
guard does not compare them (`NOT_COMPARED`); the date is what the
export withholds. `occupancy.horizon_{start,end}_us` are absolute and
are compared through the shift (`ABSOLUTE`).

**Mutations** (`/tmp/<track>/mutate.py`, each file copy-backed and
restored, 13 green after):

| mutation | reddened | count |
|---|---|---|
| `compute_critical_path` successors `sorted(...)` | `[diamond]` | 1 failed, 12 passed |
| `top_fan_in` tie on uid | `[diamond]`, `[shared_base_wide]` | 2 failed, 11 passed |
| best split tie on name | `[diamond]` | 1 failed, 12 passed |
| chain rank tie on start name | `[fan_in]` | 1 failed, 12 passed |
| blast ranking, measured branch, position dropped | `[fan_in]` | 1 failed, 12 passed |
| `LISTED` emptied | 3 topologies | 3 failed, 10 passed |
| `ABSOLUTE` emptied | 3 topologies | 3 failed, 10 passed |
| `NOT_COMPARED` emptied | 3 topologies | 3 failed, 10 passed |
| a uid not translated | all 4 captures | 4 failed, 9 passed |

Not discriminated, no capture here holds the tie: consolidation's
order, the blast ranking's count-only branch, `findings.py`'s three,
`correlate.py` (needs Plane 2). Each passed its mutation, 13 of 13.
