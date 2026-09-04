# UX-657: the priority column has no guard, and three rows have drifted

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-131 (which guarded the status column), UX-387 (one reading of a property, not two) | **Found by:** round 89, checking the rows round 88 wrote | **Serves:** anyone who sorts the backlog by priority to decide what to do next | **Topic:** guards

## Motivation

A row states its item's priority; so does the item's own header line.
`UX-131` made that pair a guarded property for **status** and `UX-387`
gave it one reading in `tools/dev_close_task.py` rather than two.
Priority got neither, and it has drifted:

```console
$ python3 - <<'PY'
import re, pathlib
S = pathlib.Path("docs/backlog/scenarios")
for name in ("README.md", "closed.md"):
    lines = (S / name).read_text(encoding="utf-8").splitlines()
    header = [l for l in lines if l.startswith("| ID |")][0]
    column = [c.strip() for c in header.strip("|").split("|")].index("Priority")
    compared = bad = 0
    for line in lines:
        row = re.match(r"^\|\s*(UX-\d+)\s*\|", line)
        if not row:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        number = int(row.group(1).split("-")[1])
        files = sorted(S.glob(f"UX-{number:04d}-*.md"))
        if not files:
            continue
        declared = re.search(r"\*\*Priority:\*\*\s*([A-Za-z]+)",
                             files[0].read_text(encoding="utf-8"))
        compared += 1
        if cells[column] != declared.group(1):
            bad += 1
            print(f"  {name} {row.group(1)}  row:{cells[column]:7s} "
                  f"file:{declared.group(1)}")
    print(f"{name}: {compared} rows compared, {bad} disagree")
PY
  README.md UX-653  row:High    file:Low
  README.md UX-655  row:High    file:Medium
README.md: 5 rows compared, 2 disagree
  closed.md UX-280  row:Low     file:Medium
closed.md: 649 rows compared, 1 disagree
```

Three of 654, which is the rate an unguarded copy drifts at rather
than a crisis. Two of the three are one round old — round 88 filed
`UX-653` and `UX-655` and wrote their rows by hand, and the hand and
the file disagreed. The third has been wrong since `UX-280` closed.

The status pair is checked in two places and neither reads this one:

```console
$ git grep -c "Priority" -- tests/unit/ tools/
tests/unit/test_the_loop_stays_fast.py:1
tools/dev_close_task.py:1
```

`test_the_loop_stays_fast.py`'s hit is a fixture's task-file header;
`dev_close_task.py`'s is the `re.sub` that appends `**Topic:**` after
the priority line. Neither compares the two copies.

`dev_close_task.py --check` prints the five properties it holds and
this is not among them, which is the shape `UX-387` named: a
contributor reading "5 checks, 0 problem(s)" cannot tell a property
that passed from one nobody wrote.

## Required Fix

The pair becomes a sixth `--check` property with one reading, beside
the status pair it is the twin of, and a clause in
`test_docs_links_and_commands.py` reads the tool the way the status
clause already does.

The two tables have different shapes — the open index is
`id, scenario, topic, priority, serves, status`, the closed one
`id, scenario, priority, depends on, status, task file` — so the cell
is found the way `table_statuses` finds its own: by what it contains,
not by column number. Measured over all 654 rows, exactly one cell per
row equals one of `High`, `Medium`, `Low`, so that read is
unambiguous, and a clause says so rather than assuming it.

The three drifted rows are corrected to what their task files say. The
task file is the record; the row is the index of it.

## Out of Scope

- Whether any of the three priorities is *right*. Declined because
  that is a product judgement and this row is about two copies of one
  fact disagreeing, which is checkable and this is not.
- The `Serves` and `Depends on` columns — same shape, no measurement
  yet. A sweep of every index column is a different row and would want
  the population derived rather than listed.
- `**Topic:**` — declined because it is already derived from the task
  files and held by `test_the_index_counts_match_the_rows_they_index`,
  so it is the arrangement this row is asking for rather than a second
  instance of the defect.

## Acceptance Test

`dev_close_task.py --check` names the priority pair among its
properties and reports the three disagreements; with the rows
corrected it reports none. Mutation: flipping either half of a pair —
the row or the task file's header — reddens the clause naming that
item.

## Outcome

**Premise:** held, and the count is exactly the three the Motivation
names. `priority_disagreements()` in `tools/dev_close_task.py` is the
one reading, imported by the suite the way `UX-387` requires, and it is
`--check`'s sixth property:

```console
$ python3 tools/dev_close_task.py --check
  ok    every row's status glyph matches its task file's
  ok    every row's priority matches its task file's
  ...
```

Before the three rows were corrected, that line read:

```text
  FAIL  every row's priority matches its task file's - 3 problem(s)
          UX-280: table says Low, UX-0280-copy-as-markdown.md says Medium
          UX-653: table says High, UX-0653-...-superseded.md says Low
          UX-655: table says High, UX-0655-...-key-population.md says Medium
```

The task file won all three: `UX-280` is Medium, `UX-653` Low,
`UX-655` Medium. The two 2026-09-04 rows were written by hand one
round before this clause existed, which is the rate the Motivation
reports rather than an accident of one session.

**The cell is found by value, and a clause says why that is sound.**
The open index is `id, scenario, topic, priority, serves, status` and
`closed.md` is `id, scenario, priority, depends on, status, task file`,
so column number is not a shared promise. Measured over every row of
both files, exactly one cell equals one of `High`, `Medium`, `Low`:

```console
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py -q -k priority
2 passed, 49 deselected in 0.29s
```

`priority_cell` answers `None` for a row with two such cells rather
than picking the first, so the pair clause cannot go quiet on one —
mutation C below is that clause failing first.

**Mutations.**

| mutation | expected | got |
|---|---|---|
| a row's priority flipped (`UX-651` Medium → High) | red | red: "table says High, ... says Medium" — 1 failed, 2 passed |
| a task file's header flipped (`UX-654` Low → High) | red | red, naming that file — 1 failed, 2 passed |
| a row given two priority-word cells | red | red: "no single priority cell ... ['UX-655']", the instrument clause first |
| a task file's `**Priority:**` removed | red | red: "no `**Priority:**` word in their first 8 lines" |
| revert all four | green | 3 passed |

The last two are the non-vacuity pair: without them a row the reader
cannot parse and a file that declares nothing both compare `None` to
`None`, and the pair clause passes by reading less.

**Deviation.** Filed with `**Topic:** process` and refused by
`test_every_open_row_carries_a_topic_from_the_closed_set`, which holds
open rows to a hardcoded eight that does not include it — while the
index's own topic table prints a `process` row. That is a second
taxonomy stated three times, and it is `UX-658`, filed rather than
absorbed here. This row is `guards`, which is what its two Depends-on
rows carry.

Running the mutations with `git checkout <file>` to revert cost the
unstaged index edits once and they were rewritten from the task files.
`--check --write` still reports `architecture.md`'s opening figure as
behind by one: that document belongs to another track this round, and
the count is re-derived at the gate.
