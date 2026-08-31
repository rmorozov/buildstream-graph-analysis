# UX-454: closing a task twice doubles its status word, and the guard cannot see it

**Priority:** Low | **Status:** 🟢 Done | **Found by:** round 70, reading `UX-453`'s own header after closing it | **Serves:** anyone reading a task file's header, and the next round that greps the status line | **Topic:** guards

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

## Outcome (round 71, 2026-08-31) — 🟢 Done

### The trigger this file named, tested and wrong

The Motivation says a *second* `--move` appends the word. It does not:
`move()` checks the open table before it substitutes, and the row is
gone by then.

```console
$ python3 tools/dev_close_task.py UX-454 --move --note "second close" --scenarios $S
UX-454 has no row in the open table (already closed?).
after close 2: **Status:** 🟢 Done
```

The real path is the ordinary one, and it needs only **one** `--move`.
The fixing guide tells an author the status lives in two places, so the
author sets the file's own marker while writing the Outcome and then
runs the tool for the row and the counts. The tool then substitutes
against a line that is already closed:

```console
author hand-set:  **Status:** 🟢 Done
old tool  --move: **Status:** 🟢 Done Done
new tool  --move: **Status:** 🟢 Done
```

That is why the count is 25 rather than the handful a genuine re-close
would explain — it fires on the *normal* closing sequence, not an
unusual one.

### The count, corrected

This file says twenty-four. It is **twenty-five**, and the discrepancy
is this file's own doing: the count was taken in the session that filed
it, after a one-file hand-repair of `UX-453` that was then reverted, so
`UX-453` was clean when counted and damaged when committed.

```console
$ git diff --name-only docs/backlog/scenarios | wc -l
25
$ git diff docs/backlog/scenarios | grep -c '^-.*Status.*Done Done'
25
```

All twenty-five were `Done Done`; no other word had doubled yet.

### The population, which is wider than one word

The file proposed naming "the closed word". The tree uses five status
vocabularies, and three of them would double the same way:

```console
$ cd docs/backlog/scenarios && grep -ho '\*\*Status:\*\* [^|]*' *.md \
    | sed 's/ *$//' | sort | uniq -c | sort -rn | head -5
    370 **Status:** 🟢 Done
     54 **Status:** 🟢 Fixed & Verified
     25 **Status:** 🟢 Done Done
     11 **Status:** 🔴 Not Started
      8 **Status:** 🟢 Done.
```

So `STATUS_WORDS` names all four and tolerates a full stop, and the
group repeats (`*` rather than `?`) — which makes the substitution
idempotent on a line that already carries a word and self-repairing on
one that carries two, rather than merely stopping the next occurrence.

### Where the guard went, and why it is three clauses

`status_marker()` answers with the glyph, because the glyph is the only
thing the two copies of the marker have to agree on. That is correct
for `UX-131`'s property and is exactly why it could not see this.
`status_words()` reads the other half, and `close_status_line()` is
`move()`'s substitution lifted out so the guard exercises **it** and
not a copy — `UX-387`'s lesson.

The three clauses are not restatements of each other, and the mutations
below are how that is known rather than asserted.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| M1 | `STATUS_WORDS = ("Not Started", "In Progress")` — the alternation exactly as it was | **`test_closing_a_task_twice_says_done_once`, alone**, printing `🟢 Done \|` → `🟢 Done Done \|` |
| M2 | the substitution made idempotent by swallowing the line (`\*\*Status:\*\* [^\|]*`) | **`test_the_verdict_prose_survives_a_close`, alone** |
| M3 | `UX-0453`'s header re-damaged to `🟢 Done Done` | **`test_no_task_file_repeats_its_status_word`, alone** |

M1 is the item's own acceptance mutation, and the clause it leaves
**green** is the point: `test_no_task_file_repeats_its_status_word`
scans a tree that is clean, so under M1 it stays green until somebody
closes a task. A single tree-scanning clause would have shipped the
defect back in and said nothing. M2 is the opposite direction — a
pattern can be idempotent and still wrong, by destroying the eleven
verdict sentences that follow an em-dash — and M3 is the one that says
the scan is not a restatement of the mechanism check.

### Deviation from the Required Fix

Two, both widening:

- The regex names **four** words rather than "the closed word", because
  `Fixed & Verified` (54 files) and `Done.` (8) double identically. The
  bullet's premise was that only one word round-trips; the measurement
  above says three do.
- Bullet three asked for "a clause that reddens on `🟢 Done Done`".
  That clause exists and is M3's, but on its own it would not have
  reddened on M1 — the mutation the acceptance test names — so the
  mechanism clause was added rather than substituted.

The third bullet's own words are what the split follows: *a guard that
compares the marker, not its parse.* Both readings are now guarded, in
the two places they can each go wrong.

### The suite

```console
$ make lint
All checks passed!

$ make test
5445 passed, 28 skipped, 1 warning in 281.07s (0:04:41)
```

Three clauses added, and the suite goes 5442 -> 5445.
