# UX-454: closing a task twice doubles its status word, and the guard cannot see it

**Priority:** Low | **Status:** 🔴 Not Started | **Found by:** round 70, reading `UX-453`'s own header after closing it | **Serves:** anyone reading a task file's header, and the next round that greps the status line | **Topic:** guards

## Motivation

Twenty-four of the 387 closed task files say `🟢 Done Done`:

```console
$ cd docs/backlog/scenarios
$ grep -l 'Status:\*\* 🟢 Done Done' *.md | wc -l
24
$ grep -l 'Status:\*\* 🟢 Done |' *.md | wc -l
363
```

The mechanism is exact and is in `tools/dev_close_task.py:256`:

```python
body = re.sub(r"\*\*Status:\*\* \S+( Not Started| In Progress)?",
              "**Status:** 🟢 Done", body, count=1)
```

The alternation names the two *open* words and not the closed one, so
against a line that already reads `**Status:** 🟢 Done` the pattern
matches `**Status:** 🟢` alone, substitutes the full closed form, and
leaves the original ` Done` behind. Closing a task a second time — a
re-close after an amended Outcome, which is ordinary — appends a word
every time.

The same file already knows this failure mode one field over. Line 268
carries a comment about not doubling `🟢 Done —` on the `closed.md`
row, and line 272 strips four possible openers before writing it. The
row was protected; the header was not.

**Why nothing caught it.** `test_the_table_status_matches_the_task_files`
compares the two copies of the marker by the status it *parses*, and it
parses a prefix. `🟢 Done Done` and `🟢 Done` parse to the same status,
so the guard reads the two copies as agreeing — which they do, on the
only thing it looks at. This is fixing guide §5 in its mildest form:
the instrument reads a proxy (the parsed status) for the thing it
names (the line the two copies actually contain).

## Required Fix

- **The regex names the closed word too**, so a re-close is idempotent
  — the property line 268 already asserts for `closed.md`.
- **The twenty-four existing headers are repaired** in the same commit,
  because a tool fix that leaves the damage behind means the next round
  reading a header still cannot tell a bug from a convention. This one
  could not: 24 files was enough to look deliberate.
- **The guard compares the marker, not its parse.** A clause that
  reddens on `🟢 Done Done` is what turns this from a thing someone
  notices into a thing CI does.

## Out of Scope

- **The four other statuses**: only the closed word round-trips through
  this path, because only closing is what the tool does. A file hand-
  edited to `🔴 Not Started Not Started` is a different bug and nobody
  has seen one.
- **`UX-449`'s question of where a check belongs: that item asks the
  same shape about skip reasons and this one should not answer it
  twice.** The two are related and separately sized.
- **Re-running `--check` over the whole backlog**: it passes today and
  will keep passing, since the parse it compares is unaffected —
  which is the point of the third bullet rather than a task of its own.

## Acceptance Test

```bash
python tools/dev_close_task.py UX-NNN --move --note "…"
python tools/dev_close_task.py UX-NNN --move --note "…"   # twice
grep '^\*\*Priority:' docs/backlog/scenarios/UX-0NNN-*.md
cd docs/backlog/scenarios && grep -c 'Status:\*\* 🟢 Done Done' *.md
make test
```

One `Done` after the second close, zero doubled headers in the tree,
and the suite green. A mutation restoring the old alternation must
redden the new clause.

## Outcome

_Not started._
