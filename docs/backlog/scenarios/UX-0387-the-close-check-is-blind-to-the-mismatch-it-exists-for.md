# UX-387: the close check is blind to the mismatch it exists for

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-131 (guard the status table against its task files), UX-336 (the loop that got slow) | **Serves:** anyone closing a task before running the full suite | **Topic:** guards

## Motivation

Review 6, checklist item 1: does the code still do what it says.

`tools/dev_close_task.py --check` is the command a contributor runs
before committing a closure — it is in the fixing guide's own loop,
and it exists because `UX-131` found the backlog index and its task
files drifting apart. `tests/unit/test_docs_links_and_commands.py`
holds the same property in the suite.

They do not agree. Reproduced deliberately on a clean tree, by
flipping one task file's own status marker and leaving the index row
alone:

```text
docs/backlog/scenarios/UX-0381-....md   **Status:** 🔴 Not Started
docs/backlog/scenarios/README.md        | UX-381 | ... | 🟢 Done |

python3 tools/dev_close_task.py --check          0 problem(s)
pytest ...::test_the_table_status_matches_the_task_files   FAILED
```

The fast command says the tree is fine; the four-minute one finds the
mismatch. Which is exactly backwards from what the two are for.

**This was not a hypothetical.** Round 61 hit it live: `UX-382`'s
closure flipped the index row and left the file's marker at 🔴,
`--check` passed, and the defect surfaced only in a full `make
test-fast` run after two more items had landed on top.

The cost compounds with `UX-336`'s own finding: the loop got slow, and
the answer was to make the *fast* checks trustworthy. A fast check that
returns a clean bill of health on a tree the suite rejects makes the
loop slower, not faster, because it teaches a contributor that the
fast check means nothing.

## Required Fix

`--check` checks the property the suite checks. The suite's clause is
the specification: for every row in the index, the status glyph in the
row equals the status glyph in the task file's own header.

Two things worth getting right rather than one:

- **One implementation, not two.** The guard and the tool asserting the
  same property by two readings is how they came to disagree. Whichever
  one reads the pair should be the one both use.
- **`--check` reports what it checked.** "0 problem(s)" is the same
  output for "I looked at four properties and all passed" and "I looked
  at three and the fourth is not implemented", and a contributor cannot
  tell those apart — which is the whole reason this went unnoticed.

## Falsification

Flip one task file's status marker without touching its index row and
run `--check`: it reports the mismatch. Flip the row without touching
the file: it reports that too, since the property is symmetric.

The other direction, so the fix is not "check everything twice": a
tree where the two agree still reports zero, and the check stays fast
enough to run before every commit — it reads two files per task and no
test collection.

## Out of Scope

- The rest of what `--check` verifies. Whatever else it holds is
  working; this is one property it does not hold at all.
- The `--move` path. It writes both halves and the round-61 case was a
  file it had never been pointed at, which is a different item
  (`--move` wrote the row for a task whose file it did not open) and
  arguably the same fix from the other side.

## Outcome (round 62, 2026-08-29) — 🟢 Done

### The gap, measured

The defect, reproduced on a clean tree by flipping one *closed* task
file's own status marker and leaving its row alone — which is the
round-61 case exactly:

```text
$ python3 tools/dev_close_task.py --check
0 problem(s)

$ pytest ...::test_the_table_status_matches_the_task_files
FAILED  1 failed in 0.28s
```

The cause is one line of scope. `UX-232` split the backlog by liveness
and `check()` kept reading the open half:

```text
rows in docs/backlog/scenarios/README.md      7    read by --check
rows in docs/backlog/scenarios/closed.md    379    read by the suite only
                                            ---
                                            386    --check answered for 1.8%
```

`BACKLOG_FILES`' own comment in the guard had already written the
warning down — "a guard that kept looking at one file would go quiet
for 225 of the 234 rows the day the split landed" — and the tool was
the guard it was describing.

### After

```text
$ python3 tools/dev_close_task.py --check
  ok    every row's status glyph matches its task file's
  ok    no closed row is left in the open index
  ok    the index's open count matches its table
0 problem(s) over 3 propert(y/ies), 386 backlog row(s)
```

And on the same mutated tree the fast check now refuses, naming the
property and the item:

```text
  FAIL  every row's status glyph matches its task file's - 1 problem(s)
          UX-382: table says 🟢, UX-0382-....md says 🔴
```

**One implementation, not two.** `table_statuses`, `file_statuses`,
`status_marker` and `backlog_files` moved into
`tools/dev_close_task.py`; `tests/unit/test_docs_links_and_commands.py`
imports them instead of keeping its own copies, so the tool and the
guard cannot drift again by construction — a clause asserts they are
the same objects.

`backlog_files()` is a call-time lookup rather than a module constant
because `--scenarios` rebinds `INDEX` and `CLOSED` after import; a
constant would have sent every reader at the real backlog while the
caller believed it was pointed at a fixture. That is guarded.

### Falsification

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | `backlog_files()` returns `(INDEX,)` — the original defect | 4 of 10 |
| M2 | the pair comparison never reports (`if False`) | 3 of 10 |
| M3 | `--check` goes back to the bare `N problem(s)` | 5 of 10 |
| M4 | `backlog_files()` frozen at first call, so `--scenarios` is ignored | 1 of 10 |
| M5 | the guard keeps its own `_table_statuses` again | 1 of 10 |

Baseline: 10 passed. `make lint` clean;
`test_docs_links_and_commands.py` 36 passed.

### Deviation from the Required Fix

- None.
