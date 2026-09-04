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
external and the repository's owner pushed all three tags.

### The gap, measured

```text
tag      commit      pyproject version   ancestor of main
v0.2.0   3ebe7e1b5   0.2.0               yes
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
`test_a_release_records_a_contract_state.py`: every release row is read
by every clause — the tag exists, it names the commit that set its
version, and that commit is reachable. Plus two clauses on `ci.yml`,
for `fetch-tags: true` and `fetch-depth: 0`, because a guard that reads
refs and history in a checkout that fetches neither is `UX-213`'s class.

Reachability is a clause of its own rather than folded into the tag
check: it is a different property, and `UX-339` removed a column from
this same document for exactly that reason.

**28 passed** in that file.

### The version floor came out, and that part still stands

The clause first read only rows at or above `0.3.0`. That floor
excluded by number and would have swallowed the next unreachable tag in
silence — the vacuous-guard shape. It is gone, and every row is read.
The floor's *replacement* — a named exemption for `v0.2.0` — was
`UX-633`, filed on a shallow clone and wrong; the removal was right on
its own merits and is what remains.

### The guard's own skip reasons went undeclared, and CI found one

`UX-449`'s scan reads skip reasons **as written**, so a new one is red
on every machine whether or not it fires. Mine was, and I did not see
it because I ran `make test-touching` — a *selector*, which does not
reach `test_every_skip_reason_is_declared.py`. `make test` would have.
It is the second entry in `CLAUDE.md`'s "Things Claude gets wrong", and
it cost one red CI run.

Both reasons are declared with counts measured, not counted by eye: 4
tag-skips on a `--no-tags` clone, 1 depth-skip on a `--depth 20` one.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| M1 | `fetch-tags: true` dropped from `ci.yml` | the tags CI clause alone |
| M2 | `fetch-depth: 0` dropped from `ci.yml` | the history CI clause alone |
| M3 | floor raised to `9.9.9` | non-vacuity alone, on 0 rows |
| M4 | a `--depth 20` clone with tags | the reachability clause declines instead of naming three reachable tags — the real defect, reproduced |

M4 is not a mutation of the code but of the *checkout*, and it is the
one that matters: it is the condition under which this file's earlier
version stated a confident falsehood.

### Deviation from the Required Fix

The Required Fix said "every release row from `0.3.0` on has a tag on
the commit its version names". Implemented for **every** row, plus
reachability, plus the two `ci.yml` clauses. The `0.3.0` floor and the
`v0.2.0` exemption both turned out to be answers to a question a
shallow clone invented — see `UX-637`.
