# UX-244: what-if's convention lives in its own docstring

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-230 (the code it documents) | **Serves:** R8 — who takes the projected number into a prioritisation meeting | **Topic:** docs

## Motivation

The third round-28 instance `UX-237` names, and the one with the
sharpest consequence: `bga whatif` publishes a projected makespan, and
what "fixed" means is the difference between a bound and a lie.

`bga/whatif.py`'s `CONVENTION` is published with every answer — *fixed*
means the element becomes instant over this run's measured durations,
with nothing else about the build assumed to change; an upper bound,
not a forecast. It is also the only place the convention is written
down outside the payload:

```text
git grep -l "upper bound, not a forecast" docs/    -> (nothing)
git grep -l CONVENTION docs/                       -> (nothing)
```

A figure travels further than its payload — into a slide, a ticket, a
meeting — and `UX-220`'s whole argument is that a number needing a
sentence should have one where the reader is.

## Required Fix

1. `docs/guides/cli.md`'s `whatif` section states the convention in the
   guide's own register, not by quoting the docstring.
2. `docs/design/architecture.md` records *why* it is an upper bound —
   the joint-saving arithmetic and what summing per-element savings
   would get wrong — since that is the reasoning a reader cannot
   reconstruct from the output.

## Out of Scope

- Restating `UX-230`'s three refusals; they are already in the payload
  and in `cli.md`.
- Changing the projection. `UX-219` measured the gap between joint and
  summed savings and the arithmetic is settled.

## Acceptance Test

The convention is findable from `docs/` without opening `bga/`, and a
guard — or `UX-241`'s review cycle, if that lands first — keeps the two
copies from drifting apart.

## Outcome — 🟢 Fixed & Verified

**Clause 1 was already satisfied when this was filed, and the filing's
measurement was a false negative.** `docs/guides/cli.md` has carried the
convention in its own register since the commit that shipped `UX-230`:

```text
$ git log --format='%ad %h %s' --date=short -S "an upper bound, not a" -- docs/guides/cli.md
2026-08-23 a9aba9c UX-230: what if you could choose the fixes

docs/guides/cli.md, "### Choosing the fixes (UX-230)":
  "Fixed" means the element becomes instant, over this run's measured
  durations, with nothing else assumed to change — an upper bound, not a
  forecast. The convention travels in every answer.
```

The filing measured `git grep -l "upper bound, not a forecast" docs/`
and got nothing. `git grep` is line-oriented, this repository's prose is
hard-wrapped at 72 columns, and the phrase wraps between `not a` and
`forecast` — so the search reported an absence that was a line break.
Nothing was wrong with the item's *reasoning*; the evidence under it was
an artefact of the instrument. Recorded here rather than quietly
skipped, because a round that finds its own premise false and does not
say so is how a false premise gets cited by the next one.

**Clause 2 was genuinely open, and is the fix.** Measured before:

```text
$ grep -n "joint_saving\|joint saving\|avings do not add" docs/design/architecture.md
463:| UX-74 | **Optimization horizon**, joint saving of the recommended set, …
```

One extensions-table row naming the feature, and no reasoning anywhere.
`architecture.md` gained a chapter — *"What a projection is, and why it
is a bound (`UX-230`, `UX-74`)"* — carrying the two things a reader
cannot reconstruct from the output:

- **"Fixed" means instant**, so a real fix that makes an element merely
  faster lands under the figure, and a fix that changes the *graph* is
  not modelled at all.
- **It is one recompute, never a sum**, and whether savings add is a
  property of the graph that is the opposite of the intuition —
  `UX-74`'s measurement on the `freedesktop-sdk` capture:

```text
  same chain      cmake-stage1 + openssl + doxygen
                  individually 1569.8s + 522.5s + 513.5s = 2605.8s
                  jointly                                  2605.8s   (adds exactly)
  different chains  cmake-stage1 + git-minimal
                  individually 1569.8s + 547.7s          = 2117.5s
                  jointly                                  1569.8s   (takes the maximum)
```

Series composes; parallel takes a maximum. Summing therefore overstates,
and overstates exactly where a reader is most likely to sum — a chain of
heavy elements that looks like a plan.

Reproduced on the committed golden fixture, where the same inequality
holds at millisecond scale:

```text
$ python -m bga.cli whatif tests/fixtures/golden/mixed_task_kinds \
      --element base.bst --element lib.bst
What if these were fixed: base.bst, lib.bst
  Makespan 0.014s -> 0.004s (saves 0.010s)
  Their individual savings add up to 0.011s, which is not what they are
  worth together (0.010s) - what one fix is worth depends on the others.
```

**The guard** — `tests/unit/test_the_whatif_convention_is_one_claim.py`,
10 tests. Three copies of one claim exist on purpose (the payload's, the
guide's, the architecture's, in three registers), so it checks *claims*
rather than wording: `CLAIMS` maps each load-bearing claim to the
phrases that carry it, and both the payload and the guide's `whatif`
section must carry all three.

It normalises whitespace before matching, and that is the item's own
lesson turned into code — `_flat()` collapses newlines, folds case and
normalises em dashes, so a reflowed paragraph cannot read as a deletion.
`TestTheGuardDoesNotRepeatTheFilingsMistake` pins that with the exact
wrapped fixture the filing tripped on.

Falsified, seven mutations:

```text
M1  CONVENTION drops "upper bound"        -> test_the_payload_carries_it[a bound and not a forecast]
M2  the guide drops "not a forecast"      -> test_the_guide_carries_it[a bound and not a forecast]
M3  architecture states one direction     -> test_it_gives_both_directions
M4  architecture argues without figures   -> + test_it_is_measured_rather_than_asserted
M5  the chapter is renamed away           -> all three of TestTheReasoningHasAHome
M6  CONVENTION drops "measured durations" -> test_the_payload_carries_it[over this run's …]
M7  the guide drops "instant"             -> test_the_guide_carries_it[fixed means instant]
```

M1 **did not land on the first attempt** and was rewritten rather than
counted: `sed` could not match `An upper bound on what the selection can
be worth, not a forecast` because the source literal wraps it across two
lines — the same hazard, one directory over. Asserting the mutation
before reading the result is what caught it; a `grep -c` that returned
`2` was the tell.

M6 and M7 exist because the first five left two of the three
parametrized claims unproven. A parametrized guard is only falsified
when each parameter has been.
