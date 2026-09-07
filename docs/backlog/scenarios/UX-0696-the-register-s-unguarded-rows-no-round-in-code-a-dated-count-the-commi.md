# UX-696: the register's unguarded rows — no round in code, a dated count, the commit body

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-497 (the register) | **Serves:** the reader who opens a module a year on and meets its history instead of its reason | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`test_the_register_is_terse.py` holds the docstring and Outcome rows.
The other two — a comment is one line of why, a commit body is eight
lines — are stated and unread. Round 93's census of what actually
drifts in comments: backticked identifiers, 1,585 checked, **0**
unresolved; round numbers in `bga/` and `tools/`, **31** lines
(`grep -rn "round [0-9]" bga tools --include=*.py`); counts and
promises — `pyproject.toml`'s "~30-module … widen in a later task",
104 modules and no task later. The stale shape is history and
numbers, not names.

## Required Fix

Three rows of the same guard. **No round in code**: the 31 lines are
grandfathered by path and may only shrink, like the docstring row.
**A count in a comment is dated or derived**: a comment containing a
bare count (`~N`, `N modules`, `N files`) must also carry a date or a
`UX-` id — the census lists today's; each is dated or its number
deleted. **The commit body**: CI reads the pull request's commits and
fails one whose body exceeds eight lines outside the footer. The
identifier check is *not* added — it found nothing, and a guard that
finds nothing is a proxy.

## Out of Scope

- `UX-NNN` ids in comments (2,948 across 81 files) — a pointer to the
  record is the register's sanctioned form of why.
- Comment density (`bga/report/json.py` 0.64 comment-to-code) — a
  ratio with no defect behind it; not a rule.

## Acceptance Test

Mutation: write `# since round 93` in `bga/blast.py` — red; write
`# about 40 modules` without a date — red; a commit body of nine
lines on a branch — the CI step reddens, and the pinned footer lines
do not count.

## Outcome

Two of the three rows built; the third dropped on measurement, which
is what the row's own rule asks for.

**No round in code.** `ROUNDS_IN_CODE` in
`test_the_register_is_terse.py`, grandfathered by path and ratcheted
like the docstring row, plus a clause that an *unlisted* module carries
none - which is what makes the table a closed population rather than a
sample.

The census is corrected. Its command was
`grep -rn "round [0-9]" bga tools`, which counted 31 lines. That
instrument is case-sensitive and the population is not:

```console
$ grep -rn  "round [0-9]" bga tools --include=*.py | wc -l
32
$ grep -rni "round [0-9]" bga tools --include=*.py | wc -l
53
```

21 lines open a sentence with `Round N`. The real population is 53
over 25 files, and the guard reads case-insensitively - a
case-sensitive one would have let two fifths through, which is the
census's own miss rather than a later drift.

**The commit body.** `tools/dev_commit_bodies.py`, a CI step, and
`test_a_commit_body_is_eight_lines.py`. Measured on the branch that
adds it: **eleven commits over the eight-line budget, worst at
fifteen**, several written while this session was arguing for
terseness. Commits before `RULE_FROM` are grandfathered by author date
rather than by a list of hashes, which the first merge would
invalidate; the cutoff sits one minute after the last of the eleven, so
every commit from this one on is bound.

**A count in a comment is dated or derived - dropped.** The row cites
`pyproject.toml`'s "~30-module … widen in a later task". It is already
gone, fixed by some round between the census and now, and nothing has
replaced it:

```console
$ grep -n "30-module\|widen in a later" pyproject.toml
(no match)
```

A detector written for it found 75 comment lines, and reading them,
all are fixture measurements - `11 elements`, `1,202 elements`,
`8 builders x 8 max-jobs`. Those are records, not claims, and the
`review` skill says to leave them. The population of counts *about the
tree* is zero. The row's own sentence decides it: "a guard that finds
nothing is a proxy" - the same reason it declined the identifier check.

| mutation | reddened | of 282 |
|---|---|---|
| `# since round 93` in `bga/blast.py` (the row's clause) | `_a_listed_file_only_loses_round_references` | 1 |
| the same line in a file not on the list | `_an_unlisted_module_carries_none` | 1 |
| a listed file loses its last reference, stays listed | `_a_file_that_lost_them_all_leaves_the_table` | 1 |
| a nine-line body, run against a synthetic repo | the tool exits 1 | 1 |
| the cutoff removed | the branch's own eleven | 11 |

**A follow-up, from watching it run.** Its first CI line read the
same whether it checked eleven commits or none - this row's own defect,
built into its fix. It now says `1 of 39 commit(s) ... checked (38
predate the rule)`. A refusal on an empty range was written beside it
and removed: **it cannot fire**, since `base..HEAD` is empty exactly
when HEAD is an ancestor of `base`. What catches a failed fetch is
`check=True`: an unresolvable base exits 1, verified.

**Deviations.**

- Two ruff findings (`S603`, `S607`) adopted with
  `dev_baseline.py --write --force --reason UX-696`. A dev tool
  shelling out to `git` is the established pattern - 45 `S603` and 23
  `S607` already recorded, `dev_close_task.py` among them.
- The rule cannot reach this branch's history without rewriting
  eleven pushed messages whose hashes `tests/tiers.py` and three task
  files cite. Grandfathering by date keeps those citations valid.

