# UX-895: the capture's own overhead is unmeasured, so Plane 2 on every build is a guess

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 6) — the owner's budget for capture is 15-25% of time and resources, and the repository publishes no overhead figure at all | **Serves:** R4 and R5 (whether Plane 2 can run on every review build), R1 (what a local `bga snapshot` costs) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

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

Gap measured: `grep -rEn "[0-9]+(\.[0-9]+)?\s*%.{0,40}(overhead|slower|hook|tracer)" docs/guides/*.md docs/design/*.md` found one unrelated hit before this row - no wall/CPU/memory number for Plane 2 anywhere.

Close: two CodSpeed Graviton runs (16 Cortex-A72, 31 GB, Ubuntu 22.04, `examples/11-serial-giant`, 2026-09-25, n=3 per arm) replaced the prose in `docs/guides/real-project.md`'s "Plane 2 costs real overhead" paragraph with a five-arm table (`none`/`capture`/`spine`/`trace`/`all`): wall +7.1% to +9.3%, CPU +1.9% to +3.2%, all five inside the 15-25% budget. Memory sampled 1/s from `/proc/meminfo` (host used-memory peak, not `host-samples/v1`'s per-process RSS - deviation from the Required Fix, which named the latter and did not anticipate a host-level reading being the one reachable): the <50 MB spread between arms sits inside the `none` arm's own spread, so the guide states the memory overhead as below this method's resolution rather than a number.

`grep -c "overhead" docs/guides/real-project.md` still finds the paragraph; `tests/unit/test_the_overhead_paragraph_names_its_measurement.py` is the Decomposition's docs guard (a percentage, a host class, a date, a budget verdict).

| mutation | reddened | count |
|---|---|---|
| every `%` figure in the overhead paragraph replaced with `N` | `test_it_names_a_percentage` | 1 |

Deviation: peak memory is host-level (`/proc/meminfo`), not `host-samples/v1`'s per-process peak RSS the Required Fix named - the only per-process-RSS-capable agent for this row was the Graviton runner, and its own capture tooling reads host memory, not `host-samples/v1`, for this project.
