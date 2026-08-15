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
| UX-01 | No built-in way to compare two runs (baseline vs. after-a-change) - real friction for the iterative-optimization workflow | High | — | 🔴 | [UX-01](UX-01-run-comparison-command.md) |
| UX-02 | No composite "how efficient is this build, is it good enough" signal - only fragmented raw numbers (certified_headroom in absolute time, confidence separately) | High | — | 🔴 | [UX-02](UX-02-composite-efficiency-score.md) |
| UX-03 | No CI-friendly gate to fail a pipeline when a build genuinely regressed | Medium | UX-01, UX-02 | 🔴 | [UX-03](UX-03-ci-regression-gate.md) |
| UX-04 | "Biggest Opportunity" names an attribution category but not what it means or what to do about it | Medium | — | 🔴 | [UX-04](UX-04-attribution-category-next-step-hints.md) |
| UX-05 | No worked, narrative "iteratively optimize a real project" tutorial - only command-reference-style docs | Medium | UX-01, UX-02 (content), not blocking to start | 🔴 | [UX-05](UX-05-optimization-walkthrough-tutorial.md) |

## Why these five

Grounded in a real, hands-on walkthrough of the current CLI against `tests/fixtures/synthetic_multi_subproject` (not a hypothetical brainstorm) - `bga analyze`, `bga sweep`, `bga floors --cold`, `bga graph --by-kind` were all run for real to check what already works well (the Key Findings block, blast-radius ranking, and `bga sweep`'s knee-point detection are all already genuinely useful decision support) versus what's actually missing. `UX-01`/`UX-02` are the two gaps that most directly block the specific next-session goal: iteratively optimizing example projects using `bga`'s own output to guide each step, until reaching a "good enough" bar the tool itself can name. `UX-03`/`UX-04`/`UX-05` are natural extensions once those two exist.

## Recommended order

1. `UX-01` and `UX-02` first, in either order - both are needed before the next optimization-iteration work session can lean on the tool instead of manual eyeballing.
2. `UX-04` is independent and small - good filler for a narrower-context session.
3. `UX-03` after `UX-01`/`UX-02` (depends on both).
4. `UX-05` last, ideally written from - or alongside - the next session's real optimization transcript rather than a hypothetical one; see its own Sequencing note for why it doesn't have to block on `UX-01`/`UX-02` landing first.
