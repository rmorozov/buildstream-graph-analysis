# UX-563: Part 8.2's `UNKNOWN` holder is a state the code cannot reach

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the maintainer deciding what the spec still promises | **Topic:** analysis

## Motivation

Spec Part 8.2 (`specification.md:625-632`) and Part 42's "Holder
set + `UNKNOWN`" row require an unidentifiable resource holder to be
reported as `blocking_tasks = UNKNOWN, ambiguous = true` — a rule
the fixing guide's hard rules repeat ("never invent data the spec
says must be UNKNOWN"). The code:

```text
bga/attribution/blame_chain.py:556-563, :780    'ambiguous': False   # "structurally always False"
bga/validation/invariants.py:323-327            sums ambiguous_wait_us from it → Part 33.4's input is a constant 0
```

The design removed the state and the spec still describes it; the
confidence gate reads a zero that can never be anything else.

## Required Fix

A decision, recorded where the spec's readers look: either the
holder-set logic regains the `UNKNOWN` outcome (with the case that
produces it in a fixture), or Part 32 gains a registry note that 8.2's
ambiguous state is retired and 33.4's term is constant — the spec's
body is not edited (§3.12), the registry is. The hard rule in
`rules.md` follows the decision.

## Out of Scope

- Any other Part — this is one state.

## Acceptance Test

Either a fixture yields `ambiguous: true` and a guard holds it, or
the registry note exists and a guard reads `'ambiguous': False` as
declared rather than as a placeholder.

## Outcome (round 83, 2026-09-03) — 🟢 Done

The registry branch, not the fixture branch. Every premise re-measured
and all three held.

```text
$ sed -n '625,632p' docs/spec/specification.md
blocking_tasks = UNKNOWN
ambiguous = true
$ grep -n "UNKNOWN" docs/spec/specification.md
628:blocking_tasks = UNKNOWN
2821:| Resource blocker is not identifiable | ... | Holder set + `UNKNOWN`; never invent a blocker |
$ git grep -n "'ambiguous'" -- bga | grep -v unambiguous
bga/attribution/blame_chain.py:556:            'ambiguous' is kept for interface stability (read by
bga/attribution/blame_chain.py:780:            'ambiguous': False,
bga/validation/invariants.py:327:        and seg.metadata.get('holder_info', {}).get('ambiguous')
```

One writer, one reader, one value. Spec Part 32 gains **32.7 Decisions
the registry records** and **32.7.1**: the state is retired, `UNKNOWN`
stays reserved, and the hard rule is enforced by the occupancy model
rather than by the flag. `rules.md`'s hard-rule row gains its guard.

**The vacuous version of this guard, and why it is not the one shipped.**
The first draft read the golden run's segments for an ambiguous holder.
Measured:

```text
$ python3 -c "... analyze_run(macro_micro/run); Counter(s.category.value ...)"
10 Counter({'EXECUTION_ON_CHAIN': 10})
with holder_info: 0
```

Zero RESOURCE_WAIT segments — it would have passed on an empty
population whatever the flag did. It now builds a genuinely saturated
wait and scores the segment twice, once with the record the classifier
returns and once with the flag forced true, so a term nothing consumes
cannot pass as a term that is zero.

| mutation | applied to | reddened | run |
|---|---|---|---|
| a new unreached method returning `'ambiguous': True` | `blame_chain.py` | `test_the_holder_flag_is_written_and_only_ever_false` only — the fixture guards stayed green, which is the discrimination | 1 failed, 4 passed |
| `'ambiguous': False` → `True` at the reachable site | `blame_chain.py` | all three code guards; the differential printed `assert 0.0 == 1.0` | 3 failed, 2 passed |
| "`UNKNOWN` remains reserved; nothing writes it." → "available to any code that needs it" | `specification.md` | `test_the_note_keeps_unknown_reserved` | 1 failed, 4 passed |

All reverted; `5 passed in 0.17s`.

**Acceptance Test** — "the registry note exists and a guard reads
`'ambiguous': False` as declared rather than as a placeholder":

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_a_retired_state_is_declared.py -v
tests/unit/test_a_retired_state_is_declared.py::TestNoCodePathWritesTheState::test_the_holder_flag_is_written_and_only_ever_false PASSED [ 20%]
tests/unit/test_a_retired_state_is_declared.py::TestTheConfidenceTermIsConstantZero::test_a_real_saturated_wait_names_a_holder_and_is_not_ambiguous PASSED [ 40%]
tests/unit/test_a_retired_state_is_declared.py::TestTheConfidenceTermIsConstantZero::test_the_term_is_live_and_the_real_record_contributes_nothing PASSED [ 60%]
tests/unit/test_a_retired_state_is_declared.py::TestTheRegistrySaysSo::test_the_note_names_the_part_and_both_consumers PASSED [ 80%]
tests/unit/test_a_retired_state_is_declared.py::TestTheRegistrySaysSo::test_the_note_keeps_unknown_reserved PASSED [100%]
============================== 5 passed in 0.18s ===============================

$ make test-touching
18 file(s) selected · 419 passed, 4 skipped in 12.60s
```

**Deviation:** the AST walk covers `bga/attribution/` only, not the
whole package. `'ambiguous'` is also a Plane 2 invocation-correlation
key (`tools/bst_native_build_tracer.py:3848`) and an unrelated
quantity; widening the walk would read that one as a holder flag.
