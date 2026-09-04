# UX-597: three release rows and no tag

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-251 (a release is a contract state), UX-581 | **Serves:** anyone trying to check out a release this repository claims to have made | **Topic:** docs

## Motivation

Direction 10's item 5. Measured in round 83:

```text
CHANGELOG.md   three release rows
git tag | wc -l   0
```

`release-guide.md` step 8 cuts the tag, and it has never been
executed. Nothing in the tree reads a tag either, so the omission is
invisible to every guard.

**Round 84 measured the three rows and found only two are tagable.**
`__version__` and `pyproject.toml` have moved exactly twice in the
project's history:

```text
bc1593557  2026-08-28  none -> 0.3.0   pyproject.toml first added here
679b9cf87  2026-09-03  0.3.0 -> 0.4.0
```

`0.2.0` was never a version anywhere in the tree — its CHANGELOG row
is retrospective, written when 0.3.0 was cut. So "three release rows
and no tag" is really *two releases and a pre-versioning row*, and a
`v0.2.0` could only ever point at a commit somebody picked.

## Required Fix

`v0.3.0` and `v0.4.0` are cut against the commits that set those
versions, and pushed. The `0.2.0` row is annotated as predating the
version it claims. Step 8 stands and a guard reads it — every release
row from `0.3.0` on has a tag on the commit its version names — so the
next release cannot leave the same gap. The guard lands with
`fetch-tags: true` on CI's checkout, because a guard that reads tags
in a checkout that fetches none is `UX-213`'s class of guard.

## Out of Scope

- Re-arguing what a release is (`UX-251`) — declined: this is the step, not the definition.
- A `v0.2.0` tag — declined: the tree has no commit that set that
  version, so any tag would name a release point invented for the tag.
  The row is annotated as pre-versioning instead.

## Blocked on

**Pushing the tags.** They are cut correctly against the two commits
above, and this session's GitHub credential refuses `refs/tags/*`:

```text
$ git push origin v0.3.0 v0.4.0
error: RPC failed; HTTP 403 curl 22 The requested URL returned error: 403
$ git push --dry-run origin claude/build-optimization-audit-hk2xne
Everything up-to-date            # branch refs are fine; tags are not
```

Deterministic across two attempts, and a policy denial rather than a
network error, so the retry rule does not apply. One paste closes it:

```bash
git tag -a v0.3.0 bc1593557 -m "0.3.0 — every document says what shape it is (2026-08-27)"
git tag -a v0.4.0 679b9cf87 -m "0.4.0 — a capture you can carry (2026-09-03)"
git push origin v0.3.0 v0.4.0
```

The guard is deliberately **not** written yet: a clause asserting the
tags exist would be red everywhere until they are pushed, and red in
CI besides — `actions/checkout@v4` fetches no tags by default, so it
needs `fetch-tags: true` in the same change.

## Acceptance Test

Mutation: add a fourth release row with no tag — red naming the row.
