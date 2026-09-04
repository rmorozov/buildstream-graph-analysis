# UX-626: a brief names a commit nobody resolved

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-510 (the brief names its base), UX-614 (the track verifies it) | **Found by:** round 85, by the UX-621 track refusing to trust it | **Serves:** a track given a base | **Topic:** guards

## Motivation

Round 85's brief for `UX-621` named its base as commit `2a7d1b8`.

```text
$ git cat-file -t 2a7d1b8
fatal: Not a valid object name 2a7d1b8
$ git log --oneline --merges -3
c57c046 Merge branch 'worktree-agent-a4bbcc3ea4301707f' …
2724972 Merge branch 'worktree-agent-a4b6a45b499adfdc3' …   ← the one described
```

The id was **written from memory rather than read**. The orchestrating
session had the merge in front of it and typed a hash it had not
copied. The track caught it, resolved the description instead of the
hash, and said so — which is `UX-614`'s check working.

The track's own reading was that the brief came from "a different
object database". That is the generous explanation and it is wrong;
recorded here because a row whose Motivation is a comfortable guess is
the shape round 84 filed six of.

`UX-510` asks that a brief name the base it will actually get. Nothing
checks that the base it names exists, and the check is one command.

## Required Fix

A brief's base is resolved before the track is launched — `git cat-file
-t` or `git rev-parse --verify` on the id, by whatever writes the
brief — or the brief names a ref rather than a hash, which resolves or
does not at the point of use.

## Out of Scope

- `UX-614`'s recovery, which handled this correctly and is closed.
- `UX-623`, which is about which refs a track can read at all.

## Acceptance Test

A brief carrying an unresolvable base, refused before a track is
launched rather than after.

## Outcome (round 85, 2026-09-04) — 🟢 Done

**Premise: held, both halves, unchanged.**

### The gap, measured

```text
$ git cat-file -t 2a7d1b8
fatal: Not a valid object name 2a7d1b8
$ git cat-file -t 2724972
commit
$ git log --oneline -1 2724972
2724972 Merge branch 'worktree-agent-a4b6a45b499adfdc3' into claude/…
```

The Motivation's refusal to accept "a different object database" is
also confirmed rather than left as an assertion: `UX-623` measured this
round that a linked worktree shares the ref store *and* the objects
with its checkout, so no track has an object database the orchestrator
lacks. Written from memory is the only explanation left standing.

### Where the check lives, and the argument

Nothing in this repository executes when a track is launched. The
hooks fire on `Bash`, `Edit` and `Write` (`.claude/settings.json`); no
tool under `tools/` runs at brief-writing time; a hook on the Agent
tool would be harness configuration, which `UX-623` declines. So a
pre-launch check can only be a command in the skill the brief is
written from, and the only thing worth guarding about a command is
that it **discriminates**. `decompose` §3 gains it, and the guards run
it over the three classes an id falls in.

`^{commit}` rather than the `cat-file -t` the Required Fix offered
first: a tree id is a valid object and `cat-file -t` answers it with
exit 0. B1 below is that difference, measured.

Also stated in the skill: `UX-614` had already put "derive the sha,
not one remembered" on this page *before* round 85 typed one from
memory. So the instruction is not repeated louder — the command is.

```text
$ python -m pytest …TestABriefsBaseResolvesBeforeItIsSent -q
4 passed, 118 deselected in 0.64s
$ make test-touching   17 file(s) selected · 599 passed, 3 skipped in 38.95s
```

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| B1 | check becomes `git cat-file -t <base>` | `…refuses_an_object_that_is_not_a_base`, `assert 0 != 0` on a tree — 1 of 4 |
| B2 | check becomes `echo <base>` | 2 of 4: the absent id and the tree both accepted |
| B3 | check reads `origin/<base>` | `…accepts_a_ref_the_orchestrator_would_write`, `assert 128 == 0` |
| B4 | cause softened to "a stale object database" | `…skill_says_when_the_check_runs`, 1 of 4 |

B2 reddens two clauses because "no check at all" fails two input
classes at once; it is the null mutation and is recorded as reddening
both rather than counted twice.

No guard of this item failed to discriminate.

### Deviation from the Required Fix

None on substance; the second option offered ("or the brief names a
ref rather than a hash") is taken **as well as** the first, and lives
in `UX-623`'s paragraph on the same page. What is *not* done, and
cannot be here: nothing makes the check run. It is a command in a
skill, and a skill is read by a session that chooses to. The second
net — the track's own `git log --oneline -1`, `UX-614` — is the one
that actually executes, one launch too late.
