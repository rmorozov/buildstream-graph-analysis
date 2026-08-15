# Active Backlog — User Scenarios & Workflow

Unlike `docs/fix-progress-tracker.md` (spec-compliance backlog against `docs/specification.md`, now closed), this backlog is about **how well `bga` actually serves its real user scenarios** - filed by walking through the tool's main use cases against its current CLI/docs and finding real friction, not spec gaps.

Same verification discipline as the closed backlog (see `docs/fixing-guide.md`): one task, one commit, a real pasted command + output before marking 🟢. Don't trust a claim of "done" (here or anywhere) without independently re-verifying it.

## Status Legend

| Status | Meaning |
|---|---|
| 🔴 Not Started | No work begun |
| 🟡 In Progress | Work underway, or claimed-done-but-unverified |
| 🟢 Done | Acceptance test run for real, output pasted into the task file |
| ⚪ Blocked / Deferred | Needs a product decision, or waiting on something else |

## Backlog

| ID | Scenario | Priority | Depends on | Status | Task File |
|---|---|---|---|---|---|
| UX-01 | No built-in way to compare two runs (baseline vs. after-a-change) - real friction for the iterative-optimization workflow | High | — | 🟢 Done — new `bga compare` subcommand | [UX-01](UX-01-run-comparison-command.md) |
| UX-02 | No composite "how efficient is this build, is it good enough" signal - only fragmented raw numbers (certified_headroom in absolute time, confidence separately) | High | — | 🟢 Done — new `efficiency_score` floor, banded + confidence-gated | [UX-02](UX-02-composite-efficiency-score.md) |
| UX-03 | No CI-friendly gate to fail a pipeline when a build genuinely regressed | Medium | UX-01, UX-02 | 🔴 | [UX-03](UX-03-ci-regression-gate.md) |
| UX-04 | "Biggest Opportunity" names an attribution category but not what it means or what to do about it | Medium | — | 🔴 | [UX-04](UX-04-attribution-category-next-step-hints.md) |
| UX-05 | No worked, narrative "iteratively optimize a real project" tutorial - only command-reference-style docs | Medium | UX-01, UX-02 (content), not blocking to start | 🟢 Done — real 2-iteration walkthrough, 48.1% improvement | [UX-05](UX-05-optimization-walkthrough-tutorial.md) |
| UX-06 | `--format raw` corrupts cross-task ordering on real multi-task logs (BuildStream's elapsed prefix is per-activity, not session-wide) - likely affects examples 01-03's historical CI numbers too | High | — | 🔴 | [UX-06](UX-06-raw-log-timestamp-corruption.md) |
| UX-07 | `run_identity.manifest_hash` collides for two different projects living in the same git repo/commit with the same target name | Medium | — | 🔴 | [UX-07](UX-07-run-identity-collides-across-sibling-projects.md) |
| UX-09 | Does `--builders` and native `max-jobs` genuinely compete for the same CPU cores? (real question, real evidence gathered) | High | — | 🟢 Done — confirmed with source citations + a real 6-configuration timing table | [UX-09](UX-09-builders-max-jobs-joint-optimization.md) |
| UX-10 | `Total Duration`/`bga compare`'s verdict is computed from tracked-task span only, not real wall-clock - can miss real pre-task overhead (sandbox staging, cache query) entirely | High | — | 🔴 | [UX-10](UX-10-total-duration-excludes-pre-task-overhead.md) |
| UX-11 | Design brainstorm: a tool to observe native-build-system behavior *inside* a single element (no jobserver, no remote-execution visibility today) | Medium | UX-09 | 🔴 (design only) | [UX-11](UX-11-native-build-system-profiler-tool.md) |

## Why these five (plus five bugs/design docs found along the way)

Grounded in a real, hands-on walkthrough of the current CLI against `tests/fixtures/synthetic_multi_subproject` (not a hypothetical brainstorm) - `bga analyze`, `bga sweep`, `bga floors --cold`, `bga graph --by-kind` were all run for real to check what already works well (the Key Findings block, blast-radius ranking, and `bga sweep`'s knee-point detection are all already genuinely useful decision support) versus what's actually missing. `UX-01`/`UX-02` are the two gaps that most directly block the specific next-session goal: iteratively optimizing example projects using `bga`'s own output to guide each step, until reaching a "good enough" bar the tool itself can name. `UX-03`/`UX-04`/`UX-05` are natural extensions once those two exist.

## Recommended order

1. ~~`UX-01` and `UX-02` first, in either order~~ - **both done.** `bga compare BASELINE CANDIDATE` and `efficiency_score` are now real; the next optimization-iteration work session can lean on the tool instead of manual eyeballing.
2. `UX-04` is independent and small - good filler for a narrower-context session.
3. `UX-03` is now unblocked (depends on `UX-01`/`UX-02`, both done) - a natural next pick.
4. `UX-05` is in progress, written from a real optimization transcript (`examples/04-critical-path-optimization` + its `optimized/` variant) rather than a hypothetical one.
5. `UX-06` and `UX-07` were found *while doing* `UX-05`'s real optimization work - both are correctness bugs (not UX-flow gaps) discovered via real `bst build` + `bga analyze`/`bga compare` runs, deferred to backlog per this session's scope rather than fixed inline since both touch widely-referenced code (the core extraction pipeline's timestamp reconstruction, and run-identity's manifest shape referenced across ~20 files). `UX-06` is the higher-priority pick next since it likely affects every example project's CI-reported numbers, not just the new one.
6. `UX-09`/`UX-10`/`UX-11` came from a second, more realistic round of `UX-05` (`examples/05-cmake-cpp-toolchain` - real CMake/C++ builds, not `sleep N`), directly testing the user's own hypothesis that `--builders` and native `max-jobs` compete for the same CPU cores. `UX-09` is done (confirmed with real evidence); `UX-10` is a real, high-priority correctness gap it surfaced (`bga compare`'s verdict can miss real wall-clock regressions concentrated in pre-task overhead); `UX-11` is a design brainstorm for a substantial future tool, not attempted this session.
