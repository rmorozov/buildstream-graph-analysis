# UX-932: a sandboxed --check --write escapes into the tree it guards, so make test is not read-only

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-688, UX-501 | **Blocks:** — | **Found by:** round 136 — a `make test` on `78b4997b` came back 4 failed with a clean diff, and the tree had a `docs/backlog/areas/tools.md` row the run itself had written | **Serves:** every session that reads a red as a finding, and every gate run taken as a reading of its own sha | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`test_a_hand_edited_count_is_reported_and_then_restored` copies the
live scenarios directory into `tmp_path` and runs the tool against the
copy:

```text
tests/unit/test_the_loop_stays_fast.py:734
    fixed = self._run("--check", "--write", "--scenarios", str(scenarios))
```

The redirect is **partial**, which is why it reads as harmless: line
1294 rebinds `SCENARIOS`, `INDEX` and `CLOSED` — what the tool reads —
and nothing it writes to the area pages.

```text
tools/dev_close_task.py:459   AREA_PAGES = REPO / "docs/backlog/areas"
tools/dev_close_task.py:1310  wrote += write_area_pages()
```

so the sandboxed `--write` writes into the **real** repository, with
rows derived from the tmp copy. Measured in a detached worktree
carrying one untracked task file and nothing else:

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_loop_stays_fast.py
1 failed (test_check_reports_a_clean_tree_as_clean), 49 passed
$ git status --short
 M docs/backlog/areas/tools.md        <- the run wrote this
?? docs/backlog/scenarios/UX-0931-....md
```

One guard writes the register and its neighbour in the same file reds
on what it wrote. On a clean tree the write is byte-identical, which is
why this has never been seen: the escape is invisible exactly when
nothing is happening.

**The module already knows about this hazard and fixed one writer of
two.** `dev_close_task.py:727` is `SCENARIOS == REPO /
"docs/backlog/scenarios"`, and its own docstring says why: "a helper
that edited the real tree from a test's temp directory is what
`test_the_loop_stays_fast` caught". That predicate guards the
architecture sentence. The area writer never asks it.

The same constant also **deletes** - read from the source, not yet
demonstrated:

```text
tools/dev_close_task.py:500   for stale in AREA_PAGES.glob("*.md"):
tools/dev_close_task.py:502       stale.unlink()
```

`keep` is derived from the redirected scenarios, so a fixture narrower
than the live tree would take real area pages out from under the suite.
Today's guard copies the whole directory, so `keep` holds every area
and nothing is removed; nothing but that copy's breadth stops it.

A third symptom falls out of the same line: `docs/backlog/areas/<area>.md`
can carry a row for a task id whose scenarios file was never
committed, which is the pairing four guards read. The one-line
reproduction needs no suite — leave `docs/backlog/scenarios/` dirty,
run that one test file, read `git status` again.

Two costs, both paid this round. `make test` is **not read-only**, so a
tree with any untracked task file in it ends the run dirty. And a gate
run that straddles a write is not a reading of its own sha at all —
the push gate keys on the sha and cannot see the tree moved under it,
which is `UX-762`'s blind spot from the other side.

## Required Fix

`AREA_PAGES` derives from `SCENARIOS` rather than from `REPO`, so a
sandboxed run's writes *and* its deletions stay inside the sandbox.
That is preferred over making the write conditional on `:727`'s
predicate: a conditional keeps the sandbox half-real, and the deletion
path would still need its own clause.

Say what `AREA_PAGES` is when no `--scenarios` is given, because the
default has to stay the real tree for the real `--check --write`.

## Out of Scope

The push gate's sha-keyed contract (`UX-762`), which is right; this row
is about the tree moving, not about what the gate reads. `UX-934`'s
adopt jobs.

## Acceptance Test

`--check --write --scenarios <tmp>` leaves `docs/backlog/areas/`
untouched — nothing added and nothing removed — and writes the derived
pages inside `<tmp>` instead; restoring the module constant reddens it.
And `pytest tests/unit/test_the_loop_stays_fast.py` on a tree carrying
one untracked task file leaves `git status --short` naming only that
file. The deletion half needs a fixture *narrower* than the live tree,
which is the case this round read but did not run.

## Outcome
