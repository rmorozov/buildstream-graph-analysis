# UX-489: the answer key asserts a ranking with no margin, on a build it runs for real

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 73, one red run of `make test-touching` while closing `UX-486` | **Serves:** the contributor whose unrelated diff is red because a real build ranked two elements the other way round | **Topic:** guards

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

**Round 75, 2026-09-02.** `UX-456`'s twenty-build method, run twice —
once with the machine to itself and once against a full `make test`,
because the defect filed here is load sensitivity and an unloaded
measurement answers the wrong question.

**The margin, measured.** Each iteration is a fresh copy of example 06
with its own `XDG_CACHE_HOME`, one cold `bst build all.bst`, then
`analyze --format json`; the same shape as the `walked` fixture.

```text
unloaded, n=20      core.bst first 20/20
  first  place   6.0 x5, 6.05, 7.0 x11, 7.05, 8.0 x2
  second place   3.0 x15, 3.05 x5
  margin min(first)/max(second) = 1.97      wall clock 37.0-52.8s

loaded (concurrent `make test`), n=7      core.bst first 7/7
  core 5.00 vs codegen.bst 4.00   margin 1.25
  core 5.00 vs lib-b.bst   5.00   margin 1.00   <- tie
  core 4.00 vs codegen.bst 4.00   margin 1.00   <- tie
  core 5.00 vs codegen.bst 4.00   margin 1.25
  core 5.00 vs codegen.bst 5.00   margin 1.00   <- tie
  core 6.00 vs lib-f.bst   4.05   margin 1.48
  core 5.00 vs codegen.bst 5.00   margin 1.00   <- tie
```

**So the spread is wider than the gap, in the regime that matters.**
The savings quantise to whole seconds. Unloaded the leader doubles the
field; loaded it drops to 4.0-6.0 while the runner-up rises to 4.0-5.0
and they tie outright on **4 of 7 runs**. On a tie the order is
whatever `max()` breaks it to — which is the hair round 73 lost by, and
the assertion was `ranked[0]["element_uid"] == "core.bst"`.

**The old clause did not reproduce in 27 tries** — `core.bst` came out
first in every build here. A clause red at a rate this fixture cannot
bound is worse than one red often: nothing local falsifies it, so it
survives until a contributor's unrelated diff meets it.

**The close.** `leads(ranked, uid)` — is `uid` among the rows tied for
the largest saving — and the clause asserts that instead of first
place. It holds in both regimes, and it still fails when an element
genuinely overtakes `core.bst`, which is the fixture losing its shape.
The runner-up is a **seven-way tie** in the unloaded data
(`codegen`, `lib-a`..`lib-f` all appear as second), so which sibling
sorts second was never a fact about the graph either.

**Mutations.** `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` cleared;
5 passed reverted.

| # | mutation | reddened | count |
|---|---|---|---|
| R1 | `leads` back to `ranked[0]["element_uid"] == uid` | `test_a_tie_still_leads` | 1 failed, 4 passed |
| R2 | `leads` accepts any named element, saving ignored | `test_genuinely_behind_does_not_lead` | 1 failed, 4 passed |
| R3 | the empty-horizon guard removed | `test_an_empty_horizon_does_not_lead` | 1 failed, 4 passed |

R1 is the one that matters: reintroducing the exact assertion this row
was filed on reddens the tie clause, so the guard set discriminates the
defect rather than the code around it.

**A weakness, named.** The five new clauses live in a file whose
`pytestmark` is `[large, walkable]`, so on a machine without `bst` they
skip along with everything else there. They need no build at all — the
horizon is synthesised — and they are in that file because the claim
belongs beside the clause it serves. On a bst-less machine the
predicate is unguarded.

**Acceptance Test, pasted:**

```text
$ python3 -m pytest tests/unit/test_the_journey_has_an_answer_key.py -q
......................                                                   [100%]
22 passed in 49.11s
```

**Deviation from the Required Fix:** the third option it offered — "the
fixture is what has to change" — is not taken. The fixture is a true
chain-dominated build and its top savings genuinely tie under load;
changing it to manufacture a margin would be inventing the fact the
clause wants to assert.
