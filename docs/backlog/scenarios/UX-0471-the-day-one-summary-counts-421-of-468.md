# UX-471: the day-one summary counts 421 task files and the tree has 468

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** none | **Found by:** architecture review 9, checklist question 3 | **Serves:** the session whose first reading of this repository is a number 47 rows out of date | **Topic:** docs

## Motivation

`CLAUDE.md` is the file every session reads before anything else, and
its tree map says:

```text
docs/backlog/scenarios/   421 task files; README.md open, closed.md closed
```

Measured:

```text
$ ls docs/backlog/scenarios/UX-*.md | wc -l
468
$ grep -c '^| UX-' docs/backlog/scenarios/closed.md
458
```

47 rows out. That is exactly the defect `UX-132` named — a figure a
later round moved and an earlier document still quotes — sitting in
the one document written to orient a reader who knows nothing else.

It is also the only figure in `CLAUDE.md` that goes stale on its own:
every other number there is a command's runtime or a rule, and this
one changes whenever any round closes anything. A document whose
correctness decays on every commit needs either a guard or no number.

## Required Fix

Either a guard that reddens when the count drifts — the same shape as
`test_the_context_map_is_the_tree.py`, which already reads `CLAUDE.md`'s
neighbourhood — or the figure is removed and the sentence keeps only
what does not decay ("`README.md` open, `closed.md` closed").

Prefer the second unless a reader can be shown to need the count: a
number nobody acts on, guarded by a test that has to be updated every
round, is a maintenance cost bought for nothing. The review that found
this could not name a decision the figure informs.

## Out of Scope

- Other figures in `CLAUDE.md` — the review checked them and they are
  command runtimes and rules, neither of which drifts with a close.
- `docs/backlog/scenarios/README.md`'s own counts — `dev_close_task.py
  --check` already guards those on both sides, so they cannot drift the
  way this one did.

## Acceptance Test

```bash
python tools/dev_close_task.py --check
grep -n "task files" CLAUDE.md
```

with either no number on that line, or a guard that fails when the
number and `ls` disagree — proved by a mutation that changes one.
