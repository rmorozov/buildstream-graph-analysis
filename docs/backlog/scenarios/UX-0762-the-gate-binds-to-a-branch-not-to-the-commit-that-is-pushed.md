# UX-762: the gate binds to a branch, not to the commit that is pushed

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-336 (the loop), UX-522 (the selector hook) | **Serves:** the session whose gate passed on a commit it did not push | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`CLAUDE.md` calls `make test` **the gate** and *"required before
marking anything done"*. It does not say *on which commit*, and
nothing checks.

Round 104 broke it twice, in one round:

- the gate ran at `67cc0d1`; the round-document commit `4879bcc`
  followed, and CI reddened on two guards that read every round
  document — a `directions.md` history row and a `docs/README.md`
  link. The round-document commit is by construction the one most
  likely to trip document guards and the one that always follows the
  gate.
- earlier, `ff41d19` was pushed with no batch gate at all;
  `docs/audits/round-104.md:79-82` records it.

The hook that exists is deliberately narrower. `.claude/hooks/
selector_before_commit.py:13-16` says so itself — it runs the
*selector* on the staged tree, *"not `make test`"*. So the repository
has commit-time enforcement for the cheap gate and none for the real
one, and the gap is invisible until CI.

## Required Fix

State the binding: the gate covers **the commit you push**, not the
branch you ran it on. Then make it checkable — record which commit a
suite run covered (the junit already carries a run; the reference
already records shas) and red on a push whose head was never covered.
A `pre-push` hook is the obvious home; the repository has none today.

The cheap alternative, if the hook is too heavy: name the commits that
always follow a gate — the round document, the ledger, the closes —
and require the gate after them rather than before.

## Out of Scope

- Replacing the batch gate with a per-item one. `UX-500` measured
  that and the answer was no.
- The selector hook (`UX-522`) — its own docstring disclaims replacing
  `make test`, so it is not the gate this row is about and widening it
  to run the suite at every commit is a different, dearer change.

## Acceptance Test

A push whose head commit no suite run covered is refused, or the guide
states the ordering and a guard reads it. Mutation: commit a document
change after a green suite and confirm the check reds where round 104
was silent.

## Outcome

**Gap measured** (round-104 shape, scratch repo: commit, marker,
further commit, push):

```text
EXIT: 2 — Blocked: HEAD (6bb7b4a5...) was never covered by a green
`make test` ... that sha is 1a795c6a..., not this one.
```

No hook existed to catch this before this row - the payload above
returned exit 0 everywhere.

**Close measured**: marker refreshed -> `EXIT: 0`, then a real push to
a local bare remote landed. An amend after the green marker refuses
again (`HEAD` moved) - confirmed, not a bug. `make check-clean` stays
green with the marker on disk.

**Verifier review, round 1 - two fixes:**

1. `is_real_push` returned on the *first* `git` invocation, so
   `git status && git push origin master` and `git push --dry-run
   origin master && git push origin master` both silently exited 0 on
   an uncovered `HEAD` - `no_bulk_add.is_bulk_add`'s own solved
   problem. Fixed by copying its loop; both now `True`. `git -C x
   push`, `VAR=1 git push`, `command git push` still bypass both -
   shared, pre-existing, filed nowhere new here.
2. The escape hatch was a silent, permanent off-switch. Now
   `BGA_SKIP_PUSH_GATE` must match `UX-\d+` (`1`/`true`/`yes` refused,
   naming why) and a real bypass prints loudly to stderr:

```text
GATE BYPASSED by BGA_SKIP_PUSH_GATE=UX-762: pushing ca781671...,
uncovered by any green `make test`. Holds for every push in this
shell until BGA_SKIP_PUSH_GATE is unset.
```

`fixing-guide.md` item 14 says exporting it disables the gate for the
shell's lifetime.

**Gate re-run on this branch's own tip.** The marker read `789d7af`
(12:15:09) against a final commit at 12:21:22 - this branch could not
have pushed itself under its own rule. Re-run with these fixes on the
tree, before the amend that records this text:

```text
$ rm -f .gate-covered && make test
7661 passed, 127 skipped, 1 warning in 322.24s (0:05:22)
$ cat .gate-covered; git rev-parse HEAD
4724b20da952afdf8de32e6838a7ee587a4c8f52
4724b20da952afdf8de32e6838a7ee587a4c8f52
```

The amend that follows changes only this text, moving `HEAD` again by
this row's own rule - correct, not a gap: the orchestrator's `make
test` at merge covers the commit actually pushed.

**Mutation table** (`test_the_gate_covers_the_pushed_commit.py`, 30
tests; scratchpad snapshot/revert, never `git checkout --`):

| mutation | reddened | count |
|---|---|---|
| drop the exemption/`:branch` check | dry-run/delete/tags/refspec | 9/30 |
| `covered == head` -> `!=` | marker-comparison clauses | 7/30 |
| non-push `git` returns `False` (round-1 bug, reinstated) | `status && push` | 2/30 |
| exempt push returns `False` | `--dry-run && push` | 2/30 |
| escape hatch never consulted | bare-flag, valid-reason clauses | 2/30 |
| `TASK_ID` widened to `.*` | bare-flag-refused only | 1/30 |
| `BYPASS` drops `{reason}` | loud-line content only | 1/30 |

Every mutation reverted; suite back to 30/30 and file byte-identical
to the snapshot each time.

**Recorded, not fixed:** `UX-766` (filed separately) - the `--force
--reason UX-762` baseline growth (2 `S607` findings) is loud only
uncommitted; `gained_since_head` matches HEAD once this commit lands,
so `make lint` is silent on it thereafter, same as every forced entry.
Also: `dev_touching`'s no-selector escalation to a full ~8-9 minute
suite run whenever the diff touches `Makefile`, with no progress
output - real friction, not fixed here.
