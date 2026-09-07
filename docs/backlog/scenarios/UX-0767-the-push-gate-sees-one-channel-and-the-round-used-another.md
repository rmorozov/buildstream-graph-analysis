# UX-767: the push gate sees one channel, and the round used another

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-762 (the gate it limits) | **Serves:** the session that trusts the push gate to cover its branch | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-762` binds the gate to the pushed commit with a Claude Code
`PreToolUse` hook that intercepts `git push`. It works, and its
verifier proved it against nine adversarial command forms.

It covers one channel. The hook fires on a **Bash tool call in a
session**; a push that reaches the remote by any other route never
meets it. Round 105 demonstrated that on the commit that added it:

```console
$ git log --oneline -1                 # the merge of UX-761 and UX-762
d580122 UX-762: the gate binds to the commit you push, not the branch
$ git log --oneline -1 origin/claude/build-optimization-audit-hk2xne
d580122
$ ls .gate-covered
ls: cannot access '.gate-covered': No such file or directory
```

`d580122` reached origin with no marker in the checkout at all — no
suite had covered it — and nothing refused. The session issued no
`git push`; the harness's own automation did, between turns. The
repository's other hooks share the shape and the exposure: CI pushes,
a person at a terminal, an editor's git integration, a `--no-verify`
equivalent — none of them route through a Bash tool call.

This does not make `UX-762` wrong. It makes its coverage a property of
the channel rather than of the branch, and the row does not say so.

## Required Fix

1. State the boundary where the gate is described — `fixing-guide.md`
   §3's item and the hook's own message — so a reader knows what the
   gate does *not* see. A guard whose coverage is unstated is read as
   total.
2. Decide whether a second, channel-independent check is worth it. The
   honest candidates: CI already re-runs the suite on the pushed
   commit and is the real backstop, in which case the hook's job is to
   catch the mistake *earlier* and its channel limit is acceptable; or
   a `pre-push` git hook, which covers every local route but must be
   installed per clone and cannot be enforced by a committed file.
   Measure the gap before building: how many pushes in rounds 103-105
   came from a channel the hook cannot see?

## Out of Scope

- The command-form gaps (`git -C x push`, `VAR=1 git push`,
  `command git push`) — `UX-762`'s verifier established those are
  shared with `no_bulk_add` and pre-existing, a different row.
- Making CI stricter (`UX-755`'s Out of Scope stands: CI is the side
  that is right).

## Acceptance Test

The documented gate says which channel it covers, and the measurement
of channel-external pushes over three rounds is recorded. Mutation: if
a second check is built, a push from outside a Bash tool call reds it
where today it lands silently.

## Outcome

_Not started._
