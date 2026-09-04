# UX-597: three release rows and no tag

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-251 (a release is a contract state), UX-581 | **Serves:** anyone trying to check out a release this repository claims to have made | **Topic:** docs

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

**Corrected round 86, by measurement.** "Never a version anywhere in
the tree" is wrong in letter. `3ebe7e1b5` does set
`version = "0.2.0"` — on a lineage `main` cannot reach:

```text
$ git merge-base --is-ancestor 3ebe7e1b5 HEAD   -> non-zero
$ git log --diff-filter=A -- pyproject.toml     bc15935 (sets 0.3.0)
```

The conclusion stands and its reason changes: not *no such version*,
but *no such version in this history*. `UX-633` carries what follows,
because a `v0.2.0` was pushed to the remote after this row declined
it, and it names that unreachable commit.

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

~~**Pushing the tags.**~~ **Unblocked round 86** — all three tags are
on the remote, pushed by the repository's owner. The 403 below is kept
because it is why this row waited two rounds:

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

## Outcome (round 86, 2026-09-04) — 🟢 Done

**Premise: half-falsified, and the block is gone.** The 403 was
external and the repository's owner pushed all three tags; "`0.2.0` was
never a version anywhere in the tree" is wrong in letter, corrected
above, and `UX-633` carries what it opens.

### The gap, measured

```text
tag      commit      pyproject version   reachable from HEAD
v0.2.0   3ebe7e1b5   0.2.0               no
v0.3.0   bc1593557   0.3.0               yes
v0.4.0   679b9cf87   0.4.0               yes

$ grep -rl 'git tag\|refs/tags' tests/  ->  nothing read a tag
$ grep -n 'fetch-tags' .github/workflows/ci.yml  ->  nothing
```

So step 8 had been executed by hand and still nothing checked it, and a
guard added without `fetch-tags` would have skipped on the one machine
that runs every commit.

### After

`TestEveryVersionedReleaseIsTagged` in
`test_a_release_records_a_contract_state.py`, five clauses over the
rows at or above `0.3.0`, plus `fetch-tags: true` on CI's checkout.
**27 passed** in that file.

Reachability is a clause of its own rather than folded into the tag
check, because it is a different property: `v0.2.0` *does* name a
commit that sets its version, and is still useless to a reader.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| M1 | `fetch-tags: true` dropped from `ci.yml` | the CI clause alone |
| M2 | floor lowered to `0.2.0` | **reachability alone** — not the version clause, which is the discrimination |
| M3 | floor raised to `9.9.9` | non-vacuity alone, on 0 rows |
| M4 | `--is-ancestor HEAD tag` instead of `tag HEAD` | reachability alone |

M2 is the one that matters: it proves the reachability clause reads
reachability rather than co-reddening with the version check.

### Deviation from the Required Fix

The Required Fix said "every release row from `0.3.0` on has a tag on
the commit its version names". Implemented, plus a third property it
did not ask for — that the commit is reachable — because `UX-339`
removed a column from this same document for exactly that reason and
the tag reintroduced it. The `v0.2.0` tag itself is left alone and
filed as `UX-633`: it was pushed by the repository's owner after this
row declined it, so removing or moving it is not this session's call.
