# UX-889: the pre-gate env check pin-checks ruff and nothing else, and its own advice moves node

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-887 | **Found by:** round 129, the 2026-09-18 audit session's closing note (never filed at the time): `dev_env_check.py` landed with ruff as its only pinned binary, while `dev_baseline.py` spawns bare `pyright` too, and the PATH advice the check prints fixes one binary by reordering the whole toolchain | **Serves:** the pipeline (the gate runs on the versions the readings were taken on) | **Topic:** guards | **Area:** tools-dev | **Shape:** judgement

## Motivation

`UX-887` built the pre-gate check around one binary. `dev_baseline.py`
has **two** producers — `ruff_findings` (`dev_baseline.py:56`) and
`pyright_findings` (`dev_baseline.py:75`), both spawned bare — and
`quality_baseline.json` records only `ruff_version`. So a pyright on
PATH that is behind the pin changes the findings list with nothing
recording that it did, which is `UX-799`'s defect one file over: the
instrument names one of its two sources.

A third binary is in the same position. Every viewer guard under
`tests/unit/` gates on `shutil.which("node")` and **skips** when it is
absent, so a box with no node runs a green suite that asserted nothing
about the page; and the dev container carries node 20, 21 and 22 side
by side, selected by which `/opt/nodeNN/bin` is first on PATH.

That is also what is wrong with the check's own remedy. Both agent
briefs and the check's failure message tell a contributor to "put
`/usr/local/bin` first on PATH". `/usr/local/bin` is not a ruff
directory — it is the container's whole tool front, and prepending it
puts it ahead of the `/opt/nodeNN/bin` entry that selects node.

## Required Fix

Read the pin for `pyright` and for `node` the way ruff's is already
read, and fail the same way. node has no pin to read, so declare one —
the **major**, not the triple, since a patch bump on another machine is
not a wrong engine. Replace the PATH-prepend advice, in the check's
message and in both agent briefs, with advice that moves one binary.

## Out of Scope

Adding `pyright_version` to `quality_baseline.json` (a separate filing
if wanted — the document's key set is guarded by `DOCUMENT_KEYS` and
changing it is a baseline migration, not this). Making CI run the check:
it is a dev pre-gate, and CI installs from the lockfile already. Whether
the viewer needs node 22 in particular — measured below, it does not;
this is a consistency pin, not a compatibility floor.

## Acceptance Test

`python3 tools/dev_env_check.py` on a box whose PATH pyright is behind
the pin exits 1 naming pyright; with node deselected it exits 1 naming
node; with all three at their pins it exits 0 and prints all three. The
guard covers the pure readings, including the one that reads `version`
out of pyright's own upgrade warning.

## Outcome

## Outcome (round 130, 2026-09-20) — 🟢 Done

**Premise:** held. Both halves were live here: PATH pyright `1.1.408`
against a pin of `1.1.414`, and `/usr/local/bin` ahead of the
`/opt/nodeNN/bin` entry that selects node.

### The gap, measured

```text
$ PATH="<a shim printing pyright 1.1.408 first>:$PATH" python3 tools/dev_env_check.py
env ok: bga at /home/claude/buildstream-graph-analysis/bga/__init__.py, ruff 0.16.7 (pinned 0.16.7)
exit=0

$ PATH="/usr/local/bin:/opt/node20/bin:..." sh -c 'command -v node; node --version'
/usr/local/bin/node   ->   v22.22.2
```

The check called the environment ok on a box whose `pyright` is six
releases behind the pin `dev_baseline.py` spawns it against. The second
reading is the advice the check itself printed: `use-node-20` selects
`v20.20.2`, and prepending `/usr/local/bin` — whose `node` symlinks to
`/opt/node22/bin/node` — returns v22. One binary fixed, another moved.

### After

```text
$ PATH="<the same shim>:$PATH" python3 tools/dev_env_check.py
env check failed:
- `pyright --version` on PATH is '1.1.408', pinned is '1.1.414' (requirements.lock). A stale
  `~/.local/bin/pyright` shadows the pinned one - call the pinned binary by its own path, or
  refresh the shadowing copy in place (`uv tool install --force pyright==1.1.414`). ...
exit=1

$ PATH="/opt/node20/bin:..." python3 tools/dev_env_check.py   # node deselected
- `node --version` on PATH is '20', pinned is '22' (.node-version). ...

$ python3 tools/dev_env_check.py    # all three at their pins
env ok: bga at .../bga/__init__.py, node 22, pyright 1.1.414, ruff 0.16.7
```

`TOOLS` is the population now — `ruff`, `pyright`, `node` — read by
`UX-799`'s §6 clause, so a fourth binary cannot land here and leave the
map naming three. node's pin is `.node-version` (new, `22`), by major: a
patch bump elsewhere is not a wrong engine.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | `pinned_version`'s `^` anchor dropped | `test_it_reads_the_ruff_pin_and_not_pytest_ruffs` (1 of 24) |
| A2 | `reported_version` written naively, `tool\s+v?(\S+)` unanchored | `test_it_reads_pyrights_answer_past_its_own_warning` (1) |
| A3 | `_NODE_MAJOR` captures the whole token, not the major | 2 clauses in `TestTheNodeMajorIsOneReadingOfBothSides` |
| A4 | `node` dropped from `TOOLS` | `test_the_population_is_the_three_binaries` (1) |
| A5 | node's pin source pointed at `.nvmrc` | 2 clauses in `TestEveryCheckedBinaryHasAPinToCheckAgainst` |

**A guard that did not discriminate, first time.** A1 and A2 first
dropped the line anchor alone and both stayed green: the version pattern
already required a leading `\d`, so `pyright version` could not match
either way — two sufficient defences, and a docstring claiming the anchor
was the one that held. The fixture now carries `pytest-ruff==0.5.0`, a
real package whose name ends in one and sorts above it, so the anchor is
load-bearing for A1; A2 mutates both at once, as the near-miss would be
written.

### Deviation from the Required Fix

None. `pyright_version` stayed out of `quality_baseline.json` (Out of
Scope: `DOCUMENT_KEYS` is guarded; changing it is a migration). Three
viewer node harnesses are 84 passed, 3 skipped under node `v20.20.2`, so
`22` is a consistency pin, not a compatibility floor.

```text
make test: 8916 passed, 174 skipped, 1 warning in 322.83s (0:05:22)
make lint: All checks passed! / clean: 567 finding(s) match tests/quality_baseline.json
```

Red on arrival, not on this diff: `UX-890` files the unaccounted flake
`ec50169` shipped; three more reds were a shallow clone.
