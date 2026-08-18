# UX-90: push-triggered captures burn runner-hours and almost never publish

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-81 (supersedes the push trigger's purpose)

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
