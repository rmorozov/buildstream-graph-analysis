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

**Round 138, 2026-09-23**

**Premise:** held — and the deletion half, read but not run when filed,
reproduces: a narrow sandbox removes 10 of 11 real area pages.

### The gap, measured

A replica of `tools/` and `docs/backlog/areas/` in the scratchpad (so
`REPO` is the replica), and a sandbox of one task file under `tools`:

```text
$ python3 replica/tools/dev_close_task.py --check --write --scenarios sandbox/scenarios
before: 11 pages
after: 1 pages
removed: ['bga-attribution.md', 'bga-diagnostics.md', 'bga-normalize.md', 'bga-replay.md',
  'bga-report.md', 'bga-structural.md', 'bga-viewer.md', 'bga.md', 'tools-native_trace.md', 'unassigned.md']
changed: ['tools.md']
sandbox areas: none
```

The first cut of the guard below ran that same mutation against this
worktree and took the real pages with it (`git status`: 10 `D`, 1 `M`,
restored by `git checkout -- docs/backlog/areas`) - so the guard now
points `REPO` at a tmp decoy too, and neither spelling of the old
constant can reach the tree from a red run.

### After

`AREA_PAGES = SCENARIOS.parent / "areas"` at import (the repository's
`docs/backlog/areas` when no `--scenarios` is given) and rebound beside
`SCENARIOS`, `INDEX` and `CLOSED` when one is.
`tests/unit/test_a_sandboxed_write_stays_in_the_sandbox.py`: the narrow
sandbox against a decoy holding `tools.md` and `bga.md` - the decoy is
byte-identical afterwards, nothing added or removed, and
`<tmp>/sandbox/areas/` holds exactly `tools.md` listing `UX-1`.

```text
$ printf '...**Area:** tools...' > docs/backlog/scenarios/UX-0999-probe.md
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_loop_stays_fast.py -q
2 failed, 48 passed in 26.08s      # both read the probe: the unstaged-row report, and the sandbox's own tools.md
$ git status --short
 M docs/contributing/fixing-guide.md          # this diff
 M tests/unit/test_the_loop_stays_fast.py     # this diff
 M tools/dev_close_task.py                    # this diff
?? docs/backlog/scenarios/UX-0999-probe.md
?? tests/unit/test_a_sandboxed_write_stays_in_the_sandbox.py
```

`docs/backlog/areas/` is not in it. `_index_off_by_a_count` now copies
the area pages beside its sandbox, so `--write changed 1 file(s)` still
names only `README.md` on a clean tree.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| B1 | `main`'s rebinding restored to `REPO / "docs/backlog/areas"` | 1 of 2: the decoy lost `bga.md` and `tools.md` was rewritten |
| B2 | `main`'s rebinding line deleted (the module value stands) | 1 of 2: the same clause |

`test_the_default_is_the_repository_s_pages` does not discriminate
against either: the default is the same path by both spellings.

### Deviation from the Required Fix

None. `tools/dev_close_task.py` joins `test_the_loop_stays_fast.py`'s
`WIDE` set at 46 against 45: this row's and `UX-935`'s guards are the
45th and 46th files naming it. The row is not moved here: a move is
the 26th close since review 25 and reds `test_the_review_has_a_cadence.py`,
so the orchestrator moves it after review 26.

```text
$ make test-touching     # taken with UX-935's row moved, since withdrawn
1 failed, 2231 passed, 4 skipped in 258.32s     # the review cadence, 26 against 25
```
