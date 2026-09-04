# UX-623: a track cannot read the tree it was copied from

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-614 (the base instruction), UX-510 (the brief names its base) | **Found by:** round 85, measuring UX-614 | **Serves:** a track checking the base it was given | **Topic:** guards

## Motivation

**Corrected round 86, by measurement — the filed text is kept below.**
The two command readings hold. The conclusion drawn from them does
not: a linked worktree shares the **ref store**, not only the object
database, so an unpushed branch resolves from it. Measured from round
86's worktree on a branch with no `origin/` counterpart:

```text
$ git rev-parse --verify round-83-registry-decisions
2d30776d66ed04d6f03705616b0ded81b6cc3ec9
$ git rev-parse --verify origin/round-83-registry-decisions
fatal: Needed a single revision
$ ls .git/worktrees/<this worktree>/
CLAUDE_BASE HEAD ORIG_HEAD commondir gitdir index locked logs
```

No `refs/` in that list: `refs/heads` and `refs/remotes` are the shared
checkout's. So "is my base the round's tip" is answerable for **every**
branch the orchestrator has, pushed or not, and the local-only case
this row was filed for does not exist.

What a track cannot read is the main checkout's *per-worktree* state —
its `HEAD`, index and working tree. Round 86 confirmed the refusal, and
also that it is broader than one flag: the `-C` redirect, git behind
process substitution, and git behind `sh <script>` were each refused,
the last two as "too complex to verify". None is needed, because the
base question is answerable against a ref.

### As filed (round 85)

`UX-614` tells a track to verify the base it actually got. Measuring
that instruction found the classifier refuses the command that would
read the other side:

```text
git reset --hard HEAD              permitted, in the worktree
git -C <main-checkout> rev-parse   refused
```

Both readings falsify a premise the brief carried. The one that
matters here is the second: a track can inspect its own branch and
`origin/*`, and cannot inspect the checkout it was branched from. So
"is my base the round's tip" is answerable only through a ref the
worktree already has — which is fine when the round's branch is
pushed, and unanswerable when it is not.

`UX-614`'s instruction is written for the answerable case. Nothing
says so, and nothing catches the other one.

## Required Fix

**Corrected with the premise.** The brief states which refs a track can
read — every ref the shared checkout has — and the base check is
written against those. Nothing is pushed and no commit id is passed for
this reason; the brief may name the round's branch.

### As filed (round 85)

The brief states which refs a track can read, and the base check is
written against those. Where the round's branch is local-only, the
orchestrating session passes the base as a commit id rather than a
branch name, or pushes first — decided, not left to the track.

## Out of Scope

- The classifier itself — harness configuration, not this
  repository's to change.
- `UX-614`'s `--ff-only` instruction — right, and unchanged.

## Acceptance Test

**Corrected with the premise.** A linked worktree resolving an unpushed
branch of the checkout it was copied from, and the documented base
check answering from that ref alone.

### As filed (round 85)

A track launched against an unpushed round branch, reporting the base
mismatch rather than reporting a base it could not check.

## Outcome (round 86, 2026-09-04) — 🔴 implemented, not closed

**Premise: falsified on its conclusion, held on its two readings.**

### The gap, measured

Both command readings reproduce. `git reset --hard HEAD` ran unrefused
in this worktree; the redirect to the main checkout was refused, and so
were two forms the filing did not know about:

```text
git -C <main-checkout> rev-parse   refused: "must target its own worktree"
git behind <(process substitution) refused: "too complex to verify"
git behind `sh <script>`           refused: "cannot be shown not to run git"
```

The conclusion drawn from them does not hold. A worktree's private git
dir has no `refs/`, so the ref store is the shared checkout's:

```text
$ git rev-parse --verify round-83-registry-decisions   2d30776…
$ git rev-parse --verify origin/round-83-registry-decisions
fatal: Needed a single revision
```

An unpushed branch of the checkout resolves. The local-only case the
row was filed for does not exist, so nothing is pushed and no commit
id is copied on this account.

### After

`implementer.md` gains `## Which refs your copy can read`, and the base
check in it is a ref question a copy can answer alone —
`git merge-base --is-ancestor HEAD <base>`, which also separates
*behind* from *diverged* before anything is moved. `decompose` tells
the orchestrator the branch resolves unpushed. Six clauses, four of
which **run** it on a checkout with no remote configured.

```text
$ python -m pytest …TestATrackCanReadEveryRefItsCheckoutHas -q
6 passed, 112 deselected in 2.44s
$ make test-touching   18 file(s) selected · 599 passed, 3 skipped in 27.03s
```

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | fenced check drops `--is-ancestor` | `…says_no_when_the_copy_has_diverged` only, `assert 0 != 0` — the behind clause stayed green, which is the distinction |
| A2 | section says "the redirect" for `git -C` | `…names_the_reading_a_copy_does_not_get`, 1 of 6 |
| A3 | `decompose` says "once you have pushed it" | `…orchestrator_is_told_the_branch_resolves`, 1 of 6 |
| A4 | sandbox copy made by `clone`, not `worktree add` | 3 of 6 — the linked-worktree property all three rest on |
| A5 | fenced check reads `origin/<base>` | `…answers_from_the_branch_name_alone`, `assert 128 == 0` |

A4 is one mutation against three clauses, which `falsify` calls
under-falsified. Recorded rather than split: the three claim one
property from three angles — the ref resolves, the private dir has no
`refs/`, the documented check answers — and no smaller mutation
removes the property.

**A clause that did not discriminate.**
`…says_no_when_the_copy_has_diverged` stayed **green** under A4, on
`git`'s exit 128 for an unresolvable ref rather than on the divergence
it names. Its own mutation (A1) reddens it correctly, so it
discriminates against the gate it was written for; against a broken
fixture it reads a fatal error as a "no". Left as is and written down.

### Deviation from the Required Fix

The Required Fix was corrected with the premise, and its remaining
half — "the brief states which refs a track can read" — is done. The
half that was dropped is "push first or pass a commit id": measured
unnecessary.
