# UX-471: the day-one summary counts 421 task files and the tree has 468

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** none | **Found by:** architecture review 9, checklist question 3 | **Serves:** the session whose first reading of this repository is a number 47 rows out of date | **Topic:** docs

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

## Outcome (round 73, 2026-09-01) — 🟢 Done

### The gap, measured

```console
$ grep -n "task files" CLAUDE.md
51:docs/backlog/scenarios/   421 task files; README.md open, closed.md closed
$ ls docs/backlog/scenarios/UX-*.md | wc -l
482
$ grep -c '^| UX-' docs/backlog/scenarios/closed.md
473
```

61 out by the time this row was worked, against 47 when it was filed —
the drift the row predicted, measurable inside one round.

### After

```console
$ python tools/dev_close_task.py --check
  ok    every row's status glyph matches its task file's
  ok    no closed row is left in the open index
  ok    the index's open count matches its table
0 problem(s) over 3 propert(y/ies), 482 backlog row(s)
$ grep -n "task files" CLAUDE.md
(exit 1)
$ grep -n "one file per task" CLAUDE.md
51:docs/backlog/scenarios/   one file per task; README.md open, closed.md closed
```

The Required Fix's second option, for the reason it gave: the review
could name no decision the figure informs, and a count kept true by a
test somebody edits every round is upkeep bought for nothing. What is
left says the thing that does not decay — one file per task, open in
`README.md`, closed in `closed.md`.

### The guard is an absence, so it needs no upkeep

`test_the_agent_configuration_holds.py::test_no_line_carries_a_count_that_a_close_makes_wrong`.
It reads counted nouns rather than digits, because `CLAUDE.md`
legitimately carries `~4m45s`, `-n auto` and section numbers, and a
clause banning digits would ban the sentences the file is for.

**It found a second one on its first run**, which the review had
passed over and this row's Out of Scope had declared checked:

```text
AssertionError: CLAUDE.md counts ['26'] of something the backlog
changes on every close
```

*"~30 sightings in ~26 items"* about the proxy defect. A running tally
of sightings decays exactly like a file count, and round 73 alone
added four — `UX-475`'s two proxy-reading guards, `UX-478`'s
stages-versus-path fixture gap and `UX-484`'s workflow guard. The
sentence now says "the most-sighted defect in this repository" and
keeps all four shapes.

What the clause deliberately does not catch is a figure frozen to a
closed item: *"Five found in `UX-420` alone"* is a fact about `UX-420`
and cannot go stale. That sentence spells its number and this clause
reads digits, which is the distinction drawn on purpose rather than by
accident.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| S1 | `421 task files` put back — the defect exactly as filed | 1 of 72 |
| S2 | `482 task files` — the **correct** count for today | 1 of 72 |

S2 is the one worth having. A guard that only reddened on 421 would go
green the moment somebody "fixed" the number to today's, and start
decaying again on the next close. The clause bans the shape, not the
error.

### Deviation from the Required Fix

None from what it asked. One thing it did not ask for and this row
did: a guard, even though the fix was removal. The row argued against
"a test that has to be updated every round" — and it is right about
*that* shape. A clause asserting an absence is the other shape: it
cannot go stale, it cost eleven lines, and it immediately paid for
itself by finding the tally the review missed.

### The runs

```text
python3 -m pytest tests/unit/test_the_agent_configuration_holds.py
                                              72 passed in 1.09s
make test                                     5627 passed, 27 skipped, 1 warning
                                              in 324.64s (0:05:24)
make lint                                     All checks passed!
```
