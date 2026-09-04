# UX-637: a shallow clone answers, and does not say so

**Priority:** High | **Status:** 🔴 Open | **Depends on:** UX-213 (guards that only guard one machine), UX-418 (the claim with no local instrument) | **Found by:** round 86, by `UX-633` being wrong | **Serves:** anyone whose guard reads history, and every future session in this environment | **Topic:** contracts

## Motivation

A session's checkout in this environment is **shallow**, and nothing in
the repository says so. `git` does not warn: it answers reachability
from the history it has, and the history it has stops at a boundary.

This is not hypothetical. It cost a filed row, a decision put to the
repository's owner, a guard, and four CI runs:

```text
$ cat .git/shallow                8 boundary commits
$ git rev-list <the PR merge ref> | wc -l                  562
$ git merge-base --is-ancestor v0.2.0 origin/main       exit 1

$ git fetch --unshallow
$ git rev-list <the same commit> | wc -l                  1202
$ git merge-base --is-ancestor v0.2.0 origin/main       exit 0
```

`UX-633` was filed on the first answer. `UX-597`'s Outcome recorded it.
The `CHANGELOG` acquired a paragraph about a "pre-merge lineage". The
round document explained the CI disagreement as a git 2.43-vs-2.55
difference. **All of it was one truncated clone**, and CI — which sets
`fetch-depth: 0` — was right every time.

Reproduced deliberately, which is what makes it a defect and not a
story: a `--depth 20` clone with the tags fetched calls **all three**
release tags unreachable.

```text
release tag(s) naming a commit no clone of this branch can reach:
['v0.4.0 -> 679b9cf8… (merge-base: no common ancestor)',
 'v0.3.0 -> bc159355… (merge-base: no common ancestor)']
```

The shape is `UX-213`'s, one turn worse. `UX-213` is a guard that
checks nothing on some machines. This is a guard that reaches the
**opposite conclusion** on some machines and states it with confidence.

## Required Fix

Landed for the release clauses in the same round, and the pattern is
the item: a clause that reads history asks
`git rev-parse --is-shallow-repository` first and **declines** rather
than concluding, with the reason declared in `KNOWN_SKIP_REASONS`; and
a second clause asserts `fetch-depth: 0` in `ci.yml`, so the decline
cannot go quiet on the machine that runs every commit.

What is left, and why this row stays open after that: **the sweep**.
Every other guard that reads `git log`, `git rev-list`, `git
merge-base` or `--diff-filter=A` has the same exposure and none of them
has been checked. `git grep -l 'rev-list\|merge-base\|diff-filter' tests/`
is the population; each hit either does not depend on depth, or gets
the same two clauses.

The developer-facing half is a sentence in the contributing guide: this
environment hands you a shallow clone, `git fetch --unshallow` is the
fix, and a history figure measured before that is worth nothing.

## Out of Scope

- Making the environment clone deeply — not this repository's to
  configure, and a guard that assumes it would be the same defect
  wearing a different premise.
- `UX-633`, which this falsified — rewritten in place as the record of
  a row filed on a truncated history.

## Acceptance Test

A `--depth 20` clone with tags fetched: the release-reachability clause
skips with its declared reason rather than naming three reachable tags
as unreachable.
