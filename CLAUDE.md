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
| `make test` | the whole suite, ~4m45s at `-n auto`. **Required before marking anything done.** |
| `make test-touching` | just the files naming the modules your diff touched (~4s) |
| `make test-small` \| `-medium` \| `-large` \| `-fast` | tiers, from measured duration in `tests/tiers.py` |
| `make test-tiers` | the suite plus a tier-drift parse, in one run |
| `make lint` | ruff + PyMarkdown; both must be clean |
| `make check-clean` | fails if an ignored path is tracked |
| `python tools/dev_close_task.py UX-NNN --move --note "…"` | the four mechanical edits that close a task |

`PYTEST_XDIST= make test-small` turns parallelism off — what you want
with `-x` or under `pdb`.

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
- **Send wide reading to a subagent.** A backlog sweep, a "where is
  this" question, a large log — `.claude/agents/researcher.md` reads it
  and returns the conclusion, so the reading never enters the main
  session's context. One CI job log ran to 63 KB in round 66.

## Architecture

```text
bga/            analysis, report, schemas · bga/viewer/  the page's modules
tools/          capture, the LD_PRELOAD hook, the spine, dev helpers
tests/unit/     one file per item, named for its claim
docs/backlog/scenarios/   421 task files; README.md open, closed.md closed
```

Section 6 of the fixing guide is the full map. Don't re-derive it.

## Things Claude gets wrong

- **Runs a tier and commits.** A tier is a *selector*. `make test` is
  the gate, and skipping it shipped a slack budget in round 66.
- **`git add -A` / `git add .`** — forbidden by §4a.1; stage paths.
- **Builds an instrument that reads a proxy** for the thing it names —
  ~30 sightings in ~26 items, in four shapes: a text scan that cannot
  tell code from data, a ratio at the noise floor, a comparison across
  machines, the wrong population. The rule is fixing guide §5; the
  three questions that catch it are in the `measure` skill.
- **Writes a guard whose setup another gate already excludes**, so it
  passes whatever the gate under test does. Five found in `UX-420`
  alone. Mutate it; do not read it.
