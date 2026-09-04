# UX-633: a release tag names a commit `main` cannot reach

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-597 (which declined this tag), UX-339 (which removed a column for this reason) | **Found by:** round 86, closing UX-597 | **Serves:** anyone checking out a release this repository claims to have made | **Topic:** docs

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

Decided, not left: either `v0.2.0` is deleted from the remote, or it is
re-pointed at a commit `main` reaches and the CHANGELOG row says which,
or the row and the tag are documented as naming a pre-merge lineage on
purpose. The reachability clause in
`tests/unit/test_a_release_records_a_contract_state.py` reads `0.3.0`
and up; whichever is chosen, it covers `0.2.0` afterwards.

**Not this session's call.** The tag was pushed by the repository's
owner after `UX-597` declined it, so deleting or moving it is theirs to
decide.

## Out of Scope

- The `0.3.0` and `0.4.0` tags — correct, reachable, and now guarded.
- Re-arguing what a release is (`UX-251`) — declined, as `UX-597`
  declined it: this is the ref, not the definition.

## Acceptance Test

Every `v*` tag in the repository reachable from `HEAD`, with the
guard's floor lowered to include `0.2.0`.
