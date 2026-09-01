# bga — BuildStream build efficiency analyzer

Two planes joined on element uid: **Plane 1** is the BuildStream
scheduler log, **Plane 2** an `LD_PRELOAD` hook plus an optional ptrace
spine. `bga analyze` reads them; `bga view` draws the page.

Read [`docs/contributing/fixing-guide.md`](docs/contributing/fixing-guide.md)
before working a task — this file is the day-one summary, that one is
the rule.

## Commands

| | |
|---|---|
| `make test` | the whole suite, ~5m30s at `-n auto`. **Required before marking anything done.** |
| `make test-touching` | just the files naming the modules your diff touched (~4s) |
| `make test-small` \| `-medium` \| `-large` \| `-fast` | tiers, from measured duration in `tests/tiers.py` |
| `make test-tiers` | the suite plus a tier-drift parse, in one run |
| `make lint` | ruff + PyMarkdown; both must be clean |
| `make check-clean` | fails if an ignored path is tracked |
| `python tools/dev_close_task.py UX-NNN --move --note "…"` | the four mechanical edits that close a task |

`PYTEST_XDIST= make test-small` turns parallelism off (for `-x` or `pdb`).

## Skills, in the order a task uses them

`orient` (where is it) → `decompose` (surfaces, input classes, tracks,
the batch gate) → `measure` → `falsify` → `verify` (close it).
`derive` before moving viewer code. Send wide reading to the
`researcher` agent and a finished change to the `verifier` agent.

## Conventions

- **Every claim is a pasted measurement**, with the command and fixture
  that produced it. "roughly 5% noise" is not a number; this repository
  has already been wrong that way.
- **One task, one commit.** The task file carries Motivation, Required
  Fix, Out of Scope, Acceptance Test and Outcome — it is the whole
  record, and a later round reads it instead of the code.
- **A new guard is not done until a mutation reddens it.** See the
  `falsify` skill.
- Task status lives in **two** places: the `**Status:**` line and the
  index row. `dev_close_task.py` edits both.
- `docs/spec/specification.md` is ground truth — read line ranges,
  never the whole file, and never edit it outside the Part 32 registry.

## Register

Terse. The *why* is one sentence; the history lives in the task file
and `git log`, never in a comment or docstring. Numbers, not narrative.
`tests/unit/test_the_register_is_terse.py` holds the first two rows.

| | |
|---|---|
| module docstring | ≤ 25 lines — the dev tools under `tools/` and the hooks; older ones only shrink |
| Outcome section | ≤ 80 lines from `UX-497` on: the gap measured, the close measured, the mutation table, the deviation |
| code comment | one line of why; rejected alternatives and rationale go in the task file |
| commit body | ≤ 8 lines; the task file is the record |

## Architecture

```text
bga/            analysis, report, schemas · bga/viewer/  the page's modules
tools/          capture, the LD_PRELOAD hook, the spine, dev helpers
tests/unit/     one file per item, named for its claim
docs/backlog/scenarios/   one file per task; README.md open, closed.md closed
```

Section 6 of the fixing guide is the full map. Don't re-derive it.

## Things Claude gets wrong

- **Runs a tier and commits.** A tier is a *selector*. `make test` is
  the gate, and skipping it shipped a slack budget in round 66.
- **`git add -A` / `git add .`** — forbidden by §4a.1; stage paths.
- **Builds an instrument that reads a proxy** for the thing it names —
  four shapes, fixing guide §5; the three questions are in `measure`.
- **Writes a guard whose setup another gate already excludes**, so it
  passes whatever the gate under test does. Mutate it; do not read it.
- **Writes the round's story into the docstring.** The register above.
