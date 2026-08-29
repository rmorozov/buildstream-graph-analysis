# UX-387: the close check is blind to the mismatch it exists for

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-131 (guard the status table against its task files), UX-336 (the loop that got slow) | **Serves:** anyone closing a task before running the full suite | **Topic:** guards

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
