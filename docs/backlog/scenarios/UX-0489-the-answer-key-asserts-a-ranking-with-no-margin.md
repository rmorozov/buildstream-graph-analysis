# UX-489: the answer key asserts a ranking with no margin, on a build it runs for real

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 73, one red run of `make test-touching` while closing `UX-486` | **Serves:** the contributor whose unrelated diff is red because a real build ranked two elements the other way round | **Topic:** guards

## Motivation

`tests/unit/test_the_journey_has_an_answer_key.py::TestTheMacroAnswer::test_the_first_thing_to_fix_is_core`
asserts an **exact first place** in a ranking computed from a build the
test performs, live, on whatever machine is running it:

```python
ranked = cold["optimization_horizon"]
assert ranked[0]["element_uid"] == "core.bst", [
    row["element_uid"] for row in ranked[:3]]
```

It went red once this round, under `make test-touching` at `-n auto`
with 102 files in flight:

```text
E   assert 'lib-c.bst' == 'core.bst'
```

and passed on the next three runs of the same clause on the same tree —
once with the diff stashed and twice with it applied. Nothing in the
diff touches the analyzer, the fixture or the ranking; what changed was
how loaded the machine was.

The clause beside it, `test_the_fixture_is_still_a_chain_dominated_build`,
is the model: it asserts `chain_share >= CHAIN_BOUND_FLOOR` with the
floor **sized from a measurement** — twenty cold builds spanning 0.853
to 0.916, and a floor 1.6 times the observed range below the lowest.
This one asserts an ordering with no margin at all, over a quantity two
elements can swap under load.

This is the shape `UX-476` closed at one level up: a gate whose
tolerance is narrower than the noise of the thing it measures reports
the noise. `UX-442`'s own filing found the same class in CI timings.

## Required Fix

- **Measure the margin.** Run the cold capture n times and record the
  horizon's top rows and their savings, so the gap between `core.bst`
  and the next element is a number rather than an assumption. The
  twenty-build method `UX-456` used for `CHAIN_BOUND_FLOOR` is the one
  to copy, and its measurement may already be re-readable.
- **Assert what the answer key is for**, with room: `core.bst` is what
  the six libraries all wait for, so the claim worth holding is that it
  is *named* and that its saving leads by more than the observed
  run-to-run spread — not that it sorts first by an unmeasured
  hair. If the spread turns out to be wider than the gap, the answer
  key is asserting something this fixture cannot support and the
  fixture is what has to change.
- **Say which it is in the clause**, the way the chain-share clause
  does: a floor with its measurement beside it, or an explicit "these
  two are within noise of each other and the key does not depend on
  their order".

## Out of Scope

- `CHAIN_BOUND_FLOOR` and `test_the_fixture_is_still_a_chain_dominated_build`
  — declined: they are already sized from a measurement (`UX-456`) and
  are the model this row copies, not something it changes.
- The analyzer's ranking rule — this row is about what a guard may
  assert about a live build, not about which element should win.
- `examples/06` itself: the fixture is fine, and a build that ranks two
  close elements either way round is a true fact about it.

## Acceptance Test

```bash
python3 -m pytest tests/unit/test_the_journey_has_an_answer_key.py -q
```

green, with the n readings of the top two elements' savings pasted into
the clause, and a stated margin — plus the clause reddening when the
fixture is mutated so that `core.bst` genuinely stops leading.

## Outcome

_Not started._
