# UX-895: the capture's own overhead is unmeasured, so Plane 2 on every build is a guess

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 6) — the owner's budget for capture is 15-25% of time and resources, and the repository publishes no overhead figure at all | **Serves:** R4 and R5 (whether Plane 2 can run on every review build), R1 (what a local `bga snapshot` costs) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

The rollout wants Plane 2 on every build type inside a 15-25% budget.
The tree's only statement about what Plane 2 costs is prose in
[`real-project.md`](../../guides/real-project.md): `--trace-opens` "runs
on a hot path", capture it deliberately. There is no number:

```text
$ grep -rEn "[0-9]+(\.[0-9]+)?\s*%.{0,40}(overhead|slower|hook|tracer)" docs/guides/*.md docs/design/*.md
docs/design/directions.md:139:41% of it; run the Plane 2 tracer against it"  - and a Plane 2 mode that
```

That single hit is about a fixture's share of something else. So the
repository asks users to pay a cost it has never measured, and the
decision it gates — Plane 2 on a review build, or nightlies only — is
the widest fork in the rollout. It is also the repository's own standing
rule turned on itself: every claim is a pasted measurement, and "real
overhead" is an adjective.

## Required Fix

Measure it, on one machine, one project, three arms against the same
target set and the same cache state:

1. `bst build` with no capture at all;
2. `bga snapshot` with Plane 2 and no `--trace-opens`;
3. the same with `--trace-opens`.

Three repeats per arm, because one capture is not a baseline
(`UX-234`'s rule, and the 33% spread the README pastes). Report, per
arm: wall clock, peak RSS from `host-samples/v1`, and total CPU. Publish
the deltas as a table in [`real-project.md`](../../guides/real-project.md)
beside the sentence it replaces, with the host class and the project
named, and state which arms fit a 25% budget.

The figure is a measurement of one machine, so the guide states it as
one: what moves it (core count, element sizes, the share of statically
linked processes the spine has to cover) belongs in the same paragraph.

## Decomposition

surfaces: `docs/guides/real-project.md` (the paragraph that says "real overhead"), `docs/design/architecture.md`'s Plane 2 cost sentence, and a recipe in the `measure` skill so a later round re-derives it rather than citing this one
guards: a docs guard that the overhead paragraph names a number, a host class and a date — the shape `test_the_register_is_terse.py` uses for pasted blocks
gap: the measurement needs a real `bst` + `bwrap` agent; no fixture can produce it
track: session's own, on the agent that has BuildStream — not an `implementer` in a worktree
gate: the round that runs the capture

## Out of Scope

Reducing the overhead. This row measures it; a row that makes the hook
cheaper is a different task with this one's number as its baseline.
Anything about the jobserver's own cost (`UX-901`).

## Acceptance Test

The guide carries a pasted three-arm table with n=3 per arm, naming the
project, the host class and the date, and a sentence saying which arms
fit 25%. `grep -c "overhead" docs/guides/real-project.md` finds the
paragraph, and the guard reddens when the number is removed.

## Outcome
