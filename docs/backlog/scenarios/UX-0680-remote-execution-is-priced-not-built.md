# UX-680: remote execution is priced, not built

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-30 (the sweep), UX-9 (what the tool sees under RE) | **Serves:** R4 and R8 deciding whether to buy it | **Topic:** analysis | **Shape:** judgement

## Motivation

Direction 5 left remote execution "deliberately unfiled"
(`directions.md:591-599`), and `UX-9` recorded why: under
BuildStream's REAPI the tool observes nothing about the remote
bottleneck. Both true, and neither answers the question a CI owner
actually asks first — *what would it buy?* Two mechanisms, priced
differently: BuildStream's REAPI moves whole sandboxes to workers
(the agent keeps staging and waiting; the worker's `max-jobs`
matters there); compiler-level RE (`recc`, `reclient`, `goma`) moves
compilations from inside a sandbox that BuildStream isolates from the
network by default. The tool half-prices both today — the sweep at
unlimited builders, and Plane 2's per-element CPU share — and never
says so.

## Required Fix

A `remote_execution_whatif` finding: the sweep run to the unbounded
builder count (what REAPI removes: the builder cap), and the per-
element compute share that a compiler-level service would move off
the agent (cc1plus/ld CPU seconds, Plane 2's `by_binary`), each as a
wall-clock projection with the assumption stated; the doc sentence
distinguishing the two mechanisms in `real-project.md`.

## Out of Scope

- Observing a remote build — `UX-9` stands.

## Acceptance Test

Example 06's finding says what unbounded builders buy (the sweep's
number) and what moving cc1plus off the agent buys (its share of the
critical path); mutation: sum the two — the additivity guard reds
(they are not additive, and the finding says so).

## Outcome

**Gap measured.** Before: `grep -c "remote-execution-whatif" bga/findings.py`
→ `0`; `bga analyze tests/fixtures/macro_micro/run --format json` (the one
committed fixture with a Plane 2 `binary_cost` — `examples/06`'s own
capture is gitignored and not present in a clone) published no such
finding.

**Close measured.** `PYTHONPATH=. python3 -m bga.cli analyze
tests/fixtures/macro_micro/run --format json`, `.findings[] | select(.id
== "remote-execution-whatif")`:

```text
severity: info
title: Remote execution, priced two ways: unbounded builders would leave
  43.2s of 43.2s; compiler offload would leave 5.2s of 43.2s - not
  additive, see below
evidence.unbounded_builders: wall_us_before 43200000, wall_us_after
  43200000, builders_before 4, builders_after 11
evidence.compiler_offload:  wall_us_before 43200000, wall_us_after 5248455
evidence.additive: false
```

Unbounded builders buy nothing here (macro_micro is chain-bound at the
configured capacity already). Compiler offload is clamped **per
element** (session's judgement): remaining wall = Σ over critical-path
elements of `max(0, dur_i − compiler_cpu_i)`, not one global clamp — a
compile cannot remove more than its own element's wall, however much
CPU concurrent compiles inside that element drew. `core.bst` (19.05s
duration, 13.89s compiler CPU) keeps 5.16s, `app.bst` keeps 0.087s, the
six `lib-*` elements' compiler CPU each exceeds their own duration and
keep 0 — 5.25s total, not the 0.0s a single global clamp gave. On
`golden` (no Plane 2), only the `unbounded_builders` half publishes.

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| `additive: False → True`, drop the non-additivity sentence from `title`/`detail` | `test_additive_is_false`, `test_the_text_carries_the_non_additivity_sentence` | 2 failed / 4 |
| compiler-offload population: all `binary_cost` elements (off-path `codegen.bst` included), not the critical path | `test_compiler_offload_matches_the_by_binary_critical_path_share` (`wall_us_before` 50,200,000 ≠ 43,200,000) | 1 failed / 4 |
| compiler-offload clamp: one global `max(0, path_us − Σcompiler_us)` instead of per element | `test_compiler_offload_matches_the_by_binary_critical_path_share` (`wall_us_after` 0 ≠ 5,248,455) | 1 failed / 4 |

Each reverted from a pristine copy; suite back to 4/4 green after every one.

**Deviation.** The compiler-offload bound is per element — a compile
removes at most its own element's wall on the critical path; the first
cut clamped once globally and read "0.0 s left" on `macro_micro` where
the per-element bound leaves 5.25 s (the verifier's arithmetic). Its
guard could not see the critical-path restriction while the clamp
saturated; recomputed per element. The reader is R4, the task's own,
since R5's section needs Plane 2 and half (a) fires without it. Two
verifier passes: HOLD (the clamp, the guard, a 10-line body), then PASS. The full gate reddened five page budgets on the finding's 128 words;
cut to 81 (`macro_micro` 7,251 → 7,182 px landed) and the budgets moved
with the measurement the way `UX-681` and `UX-683` moved them.
