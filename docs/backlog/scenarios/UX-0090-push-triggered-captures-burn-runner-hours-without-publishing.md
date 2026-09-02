# UX-90: push-triggered captures burn runner-hours and almost never publish

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-81 (done — which superseded the push trigger's purpose) | **Topic:** capture

## Motivation

Of the 24 `Real-project capture` runs to date: 4 succeeded, 2 failed
usefully (the bwrap/apparmor discovery), and **17 were cancelled** — each
new push to a busy working branch cancels the in-flight ~65-minute
capture via the `cancel-in-progress` concurrency group, several after
25–57 runner-minutes. On 2026-08-18 alone, five push-triggered runs were
cancelled and none published. The `push` path filter also evaluates
across the whole pushed commit range, so docs-only pushes at HEAD still
fire it.

The push trigger exists so capture-tooling changes get exercised — a
real need, but one that does not require a full 65-minute capture per
push to a branch where pushes arrive minutes apart.

## Required Fix

Once UX-81's `schedule:` + `workflow_dispatch` are the data-producing
paths: drop the `push` trigger, or reduce it to a cheap smoke variant
(lint the workflow, run the warm-phase guard against a stub, no build),
or keep the full capture but with `cancel-in-progress: false` plus a
`paths` filter evaluated against HEAD only. Whichever is chosen, a push
storm must no longer be able to spend hours of runner time producing
nothing.

## Out of Scope

- The publish/history mechanics (UX-81).

## Acceptance Test

Two pushes five minutes apart to a `claude/**` branch touching a capture
tool: total runner time consumed by this workflow for the pair is
bounded (smoke-sized, or one uncancelled capture) and the run ledger
shows no >20-minute cancelled run caused by the second push.

## Fix Implemented

The `push` trigger is gone. Of the three options the Required Fix
offered, dropping it is the one the evidence supports: the need it served
— *capture-tooling changes should be exercised* — is **already met, on
every push and pull request, by CI's own `bst-examples` job**, which runs
`bst_native_build_tracer run` against a real sandboxed build of
`examples/06`, and by `tests/unit/test_rebuild_set.py` for the cut
computation. A smoke variant of this workflow would have duplicated that
at extra cost.

`UX-81` is what made this safe: `schedule:` + `workflow_dispatch` are now
the data-producing paths, so removing the push trigger removes a cost
rather than a capability.

`cancel-in-progress` is kept, deliberately. Two *dispatches* of the same
ref racing for the same publish refs is a real hazard; with the push
trigger gone, the concurrency group can no longer cancel a capture that a
push merely happened to overlap.

### One more data point, produced while fixing this

Pushing the `UX-86` commit on this very branch fired run **27** — a fresh
~65-minute capture nobody asked for — because the commit touched
`.github/workflows/real-project-capture.yml`. That is the 18th instance
of the behaviour this task describes, caused by the task's own fix
landing, which is about as direct a reproduction as a scheduling defect
gets.

## Verification Log

Fixed 2026-08-18. The 17-of-24 ledger is from `UX-90` as filed; run 27
was observed live via the Actions API while this change was being
written. The claim that `bst-examples` already exercises the tracer is a
read of `.github/workflows/ci.yml`'s own
"Build + extract + analyze + compare 06-macro-micro-optimization" step,
which ends in a real `bst_native_build_tracer run` invocation.
