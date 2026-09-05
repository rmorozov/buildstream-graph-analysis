# UX-693: the lint rule set widened by layer, in one auto-fix commit, with the tools pinned

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Serves:** the implementing session, whose edit hook then reads the same rules the gate reads | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`pyproject.toml`'s `[tool.ruff.lint]` selects `F` alone, under a
comment that calls the tree "~30-module" and promises to widen the set
"in a later, separate task". The tree has 104 modules; the task never
came. `ruff check bga tools --select <family> --statistics`, round 93:

```text
UP    1378   (UP006 1162, UP035 151 — py39 typing spelled the old way)
S       87   (S603 38, S607 18, S108 7, S105/S106 2, S506 1)
SIM     37   (SIM115 11, SIM105 7)
B       12   (B007 7, B904 5)
ERA001   7   commented-out code
RUF100  23   unused `# noqa` — of 286 in bga/tools/tests
T201   355   print — tools/ prints by design; no per-file rule says so
```

`ruff>=0.6` floats, so the same configuration can hold a different
rule set next month.

## Required Fix

Three shelves. **Auto-fixed** now, enforced from the next commit:
`UP`, `SIM`, `B`, `ERA`, `RUF100`, `C4`, `I` — `ruff check --fix` in
one commit whose diff is the fixer's and nothing else (the suite is
the judge; a fix that reddens a guard is reverted, not suppressed).
**Per-file by layer**, not per-line: `tools/**` ignores `T201`;
`tests/**` ignores the annotation and docstring families; `bga/**`
ignores nothing. **Pinned**: `ruff==<x.y.z>` in the dev extra and the
same pin in the edit hook's environment. The stale comment is replaced
by one line of why and the id of this task. `S` and `C901` are not
selected here — they enter the baseline (`UX-694`).

## Out of Scope

- `S` and `C901` as zero-tolerance rules — 87 and 84 findings cannot
  reach zero in one commit; they are baselined under `UX-694` and
  burnt down under `UX-705`.
- Formatting (`ruff format`, `E`/`W`) — a reformat commit hides the
  fixer's diff; a separate task once the auto-fix shelf has landed.

## Acceptance Test

`ruff check bga tools tests .claude/hooks` is clean under the widened
set; `make test` green on the fixer's commit; `pip show ruff` matches
the pin; mutation: add one `# noqa: F401` nobody needs — `RUF100`
reddens `make lint`.

## Outcome

**The gap, measured.** `select = ["F"]` under a comment naming a
30-module tree; `ruff>=0.6` floating (0.15.8 installed). Under the
widened set, `ruff check bga tools tests .claude/hooks --select <family>
--statistics`:

```text
I 289 · UP 1,497 · SIM 172 · C4 43 · RUF100 288 · B 30 · ERA 11
```

**The close, measured.** The fixers, safe then `--unsafe-fixes`:

```text
Fixed 709 errors                       (safe)
Found 1552 errors (1509 fixed, 43 remaining)   (unsafe)
370 files changed, 2,270 insertions(+), 2,174 deletions(-)
by hand: B904 5 · SIM102 5 · SIM117 3 · UP031 7 · UP035/F401 6 · B017 2 · B007 1 · B005 1
ruff check … → All checks passed!   make lint → All checks passed!
make test → 1 failed, 7,161 passed; the one a text scan (below); 20 passed after
```

`ruff==0.15.8` pinned in the dev extra; `tools/**` ignores `T201`,
`tests/**` ignores `C408`.

**Mutations.**

| mutation | gate / guard | result |
|---|---|---|
| `import os  # noqa: F401` appended to `bga/progress.py` | `make lint` | red, `RUF100 Unused noqa directive` |
| `def _mut(x: List[int])` with `from typing import List` | `ruff check` | red, `UP006` and `UP035` |
| `progress = None` in place of the import in `bga/analyzer.py` | `test_the_minutes_inside_analyze.py` | 1 failed |

**Deviation.** `ERA` is not selected: its 11 findings were 11 prose
comments (`# Floors (M3)`, a schema sketch, a formula) and no code.
`SIM115` (114 sites, no fixer) is ignored until the baseline of
`UX-694` holds it by identity. One guard read `"import progress"` as
text and went red when the sorter merged the import with its
neighbour; it reads the module now (`UX-403`'s shape). The safe
fixers ran once from a `--fix-only` measurement before the config
landed; the tree is the same either way.
