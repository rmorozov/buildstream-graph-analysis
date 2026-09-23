# UX-948: the push gate is the whole suite, and CI runs the same suite again before anything merges

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-762, UX-885 | **Blocks:** — | **Found by:** round 138 — Ruslan in the project thread, 2026-09-23 08:42 and 08:43 | **Serves:** every track that pushes a `claude/*` branch from a shared 4-core box | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

The owner's question, 2026-09-23 08:42: "do we really need full suits on
agent? as we anyway wait for full ci?" His "yes" at 08:43 accepted the
proposal: pushes to a `claude/*` branch gate on `make test-touching`,
`make lint`, `dev_sizes.py --check` and `dev_close_task.py --check`;
CI's full matrix is the real gate; nothing merges without green CI.

Measured by the orchestrator this round:

- one local `make test`: 17.5 min alone, 22-26 min beside other tracks, 4 cores;
- six concurrent runs: 76 min, 43 false reds (node `TimeoutExpired`, load average about 400);
- the CI-only `sizes` job caught growth on #275 and #276 that a green local `make test` could not see.

And plain `make test-touching` cannot be the push check as written: it
diffs against `HEAD`, so once the change is committed it selects nothing.

## Required Fix

A `make push-check` target running the four checks, the selector
against the merge-base with `origin/main`, writing `.gate-covered` with
HEAD's sha only when all four pass. The push hook keeps its contract
(the marker names the pushed sha) and names `make push-check`. Every
document stating the old rule states the new one.

## Out of Scope

`make test`'s own recipe and marker, kept. CI's workflow. The selector's
`EVERYTHING` list, which makes a `Makefile` change select the whole tree.

## Acceptance Test

`python3 -m pytest -q tests/unit/test_the_gate_covers_the_pushed_commit.py`
green; each mutation that lets the marker be written past a red check
reddens it.

## Outcome

**Round 138, 2026-09-23** — fixed; the row move waits on review 26 (`test_the_review_has_a_cadence.py`), as rule 5 of the round says.

### The gap, measured

```text
$ python3 tools/dev_touching.py --list          # this commit as HEAD, clean tree
Nothing changed against HEAD - `make test-touching` has nothing to select. Run `make test-small` for the tier.
$ python3 tools/dev_touching.py --base "$(git merge-base HEAD origin/main)" --list | wc -l
583
```

### After

`make push-check` = `lint` (PyMarkdown, ruff, `dev_baseline.py --check`)
→ `dev_touching.py --base <merge-base>` → `dev_sizes.py --check` →
`dev_close_task.py --check` → `.gate-covered`. `make -n push-check`:

```text
python3 tools/dev_baseline.py --check
base=$(git merge-base HEAD origin/main) && python tools/dev_touching.py --base "$base"
python3 tools/dev_sizes.py --check
python3 tools/dev_close_task.py --check
git rev-parse HEAD > .gate-covered
```

`TestThePushCheckWritesTheMarkerOnlyOnGreen` runs the real `Makefile`
in a scratch repo whose `python`, `python3` and `ruff` are stubs failing
on one named check: all green writes HEAD's sha; each of the six checks
red, or no merge-base, writes nothing, and the run's last echoed line is
the check that failed.

```text
$ python3 -m pytest -q tests/unit/test_the_gate_covers_the_pushed_commit.py
40 passed in 4.05s
```

Stated in `CLAUDE.md` (commands table, pipeline, first trap),
`rules.md` §3 (the rule re-slugged, the hook's marker re-pointed),
fixing guide item 14 and §7a step 7, the `verify` and `decompose`
skills, the `verifier` agent, the hook's docstring and three messages.

### Mutations

| mutation | red |
|---|---|
| marker written as the recipe's first line | 4 (`dev_touching`, `dev_sizes`, `dev_close_task`, no merge-base) |
| `-` on the three check lines (errors ignored) | the same 4 |
| `lint` dropped as a prerequisite | 4 (recipe clause; `pymarkdown`, `ruff`, `dev_baseline` red) |
| `--base "$$base"` dropped | 1 (recipe clause) |
| hook `MESSAGE` names `make test` again | 1 |

Each reverted, green after.

### Deviation

The push itself took `BGA_SKIP_PUSH_GATE=UX-948` rather than dogfooding
`make push-check`: this diff touches `Makefile`, which is in
`dev_touching.EVERYTHING`, so the selector step selects all 583
files — the local full suite rule 12 forbids. The guard files the diff
names ran instead (below). A `Makefile`, `conftest.py` or `tiers.py`
change makes `make push-check` a full suite; that is `EVERYTHING`'s
design, left as it is.

```text
$ make lint                              # exit 0
clean: 573 finding(s) match tests/quality_baseline.json; ...
$ python3 tools/dev_sizes.py --check
sizes ok: 133 file(s) measured, none above the cell tests/quality_reference.json records
$ python3 tools/dev_close_task.py --check
0 problem(s) over 10 propert(y/ies), 942 backlog row(s)
$ pytest -q -n 3 <106 files: the selection without Makefile, plus every guard reading it>
2969 passed, 6 skipped in 160.12s (0:02:40)
```
