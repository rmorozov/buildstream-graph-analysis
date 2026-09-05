# UX-693: the lint rule set widened by layer, in one auto-fix commit, with the tools pinned

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the implementing session, whose edit hook then reads the same rules the gate reads | **Topic:** guards | **Shape:** judgement

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
