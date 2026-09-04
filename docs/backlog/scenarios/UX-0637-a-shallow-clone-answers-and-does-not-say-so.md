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

## Outcome (round 87, 2026-09-04) — 🟢 Done

**Premise:** half held, half falsified. The sweep is real; its
population was **one file**, already fixed in round 86. What was left
is the prospective guard and the guide sentence, not a second repair.

### The sweep, measured

```text
$ git grep -l 'rev-list\|merge-base\|diff-filter' tests/
tests/unit/test_a_release_records_a_contract_state.py
```

That file already carries the decline (`_shallow()` `:342`, the skip
`:420`, the `fetch-depth: 0` clause `:437`). Widened by hand to every
subcommand whose answer moves with depth (`log`, `describe`, `blame`,
`shortlog`) the population is **two**: `test_the_verification_log_is_true`
reads `git log -1 -- <doc>` and declines on the **graft boundary**
instead — deliberately, since this repository is worked in a grafted
clone that is shallow *and* carries the commits that guard needs, so
`--is-shallow-repository` there would switch a working guard off.
Nothing else in `tests/` reads history: `ls-files`, `check-ignore`,
`grep`, `rev-parse HEAD`, `show <ref>:<path>` are content, not ancestry.

### The Acceptance Test

This session's clone is **not** shallow (1226 commits, no
`.git/shallow`), so the case was built:

```text
$ git clone --depth 20 file://…/.git shallow20 && git -C shallow20 \
    fetch --depth 20 origin 'refs/tags/*:refs/tags/*'    v0.2.0 v0.3.0 v0.4.0
$ git -C shallow20 rev-parse --is-shallow-repository     true  (62 commits)
$ python3 -m pytest tests/unit/test_a_release_records_a_contract_state.py -q -rs
SKIPPED [1] …:421: this checkout is shallow, so its history stops at a
boundary and reachability here is not the tree's answer
27 passed, 1 skipped in 0.28s
```

With `if _shallow():` mutated to `if False:` in that clone the
Motivation's output returns — three reachable tags called unreachable:

```text
E  release tag(s) naming a commit no clone of this branch can reach:
   ['v0.4.0 -> 679b9cf8… (merge-base: no common ancestor)',
    'v0.3.0 -> bc159355…', 'v0.2.0 -> 3ebe7e1b…']
```

`test_a_guard_that_reads_history_declares_its_depth.py` (11 clauses)
makes the sweep standing over `git ls-files tests/`, so the third
history-reading guard cannot arrive undeclared; the developer half is in
`fixing-guide.md` §3, with its rules-card row.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| A1 | `_shallow()` → `return False`, its skip deleted, in the release guard | `…_says_what_a_shallow_clone_gets`, by path; 1 failed 10 passed |
| A2 | `DEPTH_DEPENDENT` loses `merge-base` | `…_are_in_it` + `…_a_sentence_does_not`; 2 failed 9 passed |
| A3 | `DECLARES_DEPTH` gains `-1`, an ordinary argv token | `…_a_literal_and_not_a_word`; 1 failed 10 passed |
| A4 | guide's `fetch --unshallow` → `fetch --deepen 50` | `…_its_clone_may_be_shallow`; 1 failed 10 passed |

**One guard of mine did not discriminate.** `declares_depth` first
excluded docstrings by AST; removing that exclusion left all 11 clauses
green, because the match is whole-constant equality and prose is never
equal to `shallow`. It did nothing, so it is gone, and the clause reads
the load-bearing property instead — a widened `DECLARES_DEPTH` (A3).

### Deviation from the Required Fix

Nothing to repair, so no second file got the two clauses. `tools/` is
outside the scan: `dev_touching.py` runs `git diff --name-only <base>`
and belonged to another track.

**Not closed here, and it cannot be:** `README.md` is shared across this
round's four tracks (`UX-501`), and flipping this file's `**Status:**`
alone reddens `dev_close_task --check` on both markers, which the commit
hook runs. Both markers move together, so `dev_close_task.py UX-637
--move` after the merge is the close. The derived loop figure moved
469 → 470; re-derive once. `make test-touching`: 812 passed, 4 skipped.
