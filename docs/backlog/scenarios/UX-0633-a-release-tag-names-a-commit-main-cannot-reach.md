# UX-633: a release tag names a commit `main` cannot reach

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-597 (which declined this tag), UX-339 (which removed a column for this reason) | **Found by:** round 86, closing UX-597 | **Serves:** anyone checking out a release this repository claims to have made | **Topic:** docs

## Motivation

All three release tags now exist on the remote. Two are what the
release guide asks for; the third is not:

```text
tag      commit      pyproject version   reachable from HEAD
v0.2.0   3ebe7e1b5   0.2.0               no
v0.3.0   bc1593557   0.3.0               yes
v0.4.0   679b9cf87   0.4.0               yes
```

`git checkout v0.2.0` succeeds and hands the reader a tree that is not
an ancestor of anything shipped. `pyproject.toml` enters this history
at `bc15935` — which sets `0.3.0` — so `3ebe7e1b5` is on a lineage that
never merged.

`UX-597` declined a `v0.2.0` on the grounds that *"the tree has no
commit that set that version"*. That was wrong in letter: a commit does
set it, just not one `main` can reach. The conclusion held for a reason
the row did not state.

This is the defect `UX-339` removed the review log's commit column for,
in a third place: **a ref that names a commit no clone can reach names
one machine.** The tag is worse than the column was, because a tag
looks like a release.

## Required Fix

**Decided by the repository's owner, round 86: the tag is kept, and
documented as naming a pre-merge lineage.** It is the only ref that
reaches the code the first release was cut from, and deleting it would
lose that for the sake of a clause.

So the version floor comes out of
`tests/unit/test_a_release_records_a_contract_state.py` entirely and is
replaced by a **named exemption**: `v0.2.0` is listed, with its reason,
and every other `v*` must be reachable. A floor at `0.3.0` excludes by
number and would swallow the next unreachable tag in silence — the
vacuous-guard shape this repository has shipped before. A named set
cannot: an unlisted tag reddens, and a listed one that stops applying
reddens too.

## Out of Scope

- The `0.3.0` and `0.4.0` tags — correct, reachable, and now guarded.
- Re-arguing what a release is (`UX-251`) — declined, as `UX-597`
  declined it: this is the ref, not the definition.

## Acceptance Test

Every `v*` tag in the repository reachable from `HEAD`, with the
guard's floor lowered to include `0.2.0`.

## Outcome (round 86, 2026-09-04) — 🟢 Done

**Premise held, and the fix is the opposite of what the row's own
Acceptance Test asked for** — see the deviation.

### The gap, measured

```text
$ git tag --list 'v*'                                v0.2.0 v0.3.0 v0.4.0
$ git merge-base --is-ancestor v0.2.0 HEAD           exit 1
$ git show v0.2.0:pyproject.toml | grep '^version'   version = "0.2.0"
```

So `v0.2.0` passes *two* of `UX-597`'s three clauses — the tag exists,
and it names a commit that sets its version — and fails only
reachability. The `0.3.0` floor was excluding a row that three clauses
out of four had no quarrel with.

### After

`FIRST_TAGGED_RELEASE` is gone. Every release row is now read by every
clause, and `UNREACHABLE_BY_DECISION = {"v0.2.0"}` carries the one
exception with its reason in the constant's comment. A sixth clause,
`test_each_named_exception_still_needs_naming`, reddens when a listed
tag stops needing the exemption.

```text
rows read by the tag/version clauses   2 -> 3
exclusions                             a version floor -> one named tag
```

**33 passed** in `test_a_release_records_a_contract_state.py`.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| P1 | `UNREACHABLE_BY_DECISION = set()` | reachability alone — the exemption is load-bearing, not decoration |
| P2 | `"v9.9.9"` added to the set | the staleness clause alone |
| P3 | `"v0.4.0"` added to the set (a reachable tag) | the staleness clause alone |

P1 is the one that matters: it shows the clause would have caught
`v0.2.0` on its own, so the exemption is a decision recorded rather
than a hole that happened to be there.

### Deviation from the Required Fix

The **Acceptance Test as filed** asked for "every `v*` tag reachable
from `HEAD`, with the guard's floor lowered to include `0.2.0`". That
presumed the tag would go. The owner decided it stays, so the clause
that ships is the same shape with the sign flipped: the floor is gone,
every tag is read, and the one that cannot be reachable is named.
Written down rather than quietly re-scoped, because the two read alike
in a diff and do not mean the same thing.
