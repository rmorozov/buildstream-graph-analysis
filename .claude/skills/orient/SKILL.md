---
name: orient
description: Find where something lives in this repository without reading widely - a finding id, a schema key, a viewer section, the test that names a module, the task file that explains a mechanism. Use when a question starts with "where" or "which file", before opening anything larger than a task file.
---

# orient

The context map is [fixing guide](../../../docs/contributing/fixing-guide.md)
§6 and it says which *directory* owns what. These are the lookups below that level, each one command, each
returning lines rather than files. Every session re-derives them; a
session that pays for reading is a session that runs out before the
Outcome is written.

| I want… | run |
|---|---|
| where a finding id is emitted, and its provenance rule | `grep -rn "'<finding_id>'" bga/findings.py bga/provenance.py` |
| which command publishes a key, and its unit hint | `grep -n "<key>" bga/schemas.py` |
| which viewer section renders a key, in which chapter | `grep -n "<key>" bga/viewer/chapters.js bga/viewer/*.js` |
| the tests that name a module | `make test-touching ARGS=--why` after touching it, or `grep -ln "<module>" tests/unit/*.py` |
| the task file that explains a mechanism or a number | `git grep -l "<identifier or figure>" docs/backlog/scenarios/` |
| why a line is the way it is | `git log -L<start>,<end>:<file> --oneline` — the task id is in the subject |
| what a make target or dev tool does | `sed -n 1,25p tools/dev_touching.py` (any of them) — the docstring is capped at 25 lines (`UX-497`) |
| which tier a test file is in, and why | `grep -n "<file>" tests/tiers.py` |
| every skip the suite can take, as written | `python3 -m pytest tests/ --co -q 2>/dev/null \| tail -1` then `tests/skip_reasons.py` |
| the round that filed or closed an item | `grep -n "UX-<n>" docs/backlog/scenarios/README.md docs/backlog/scenarios/closed.md` |

Four rules that keep the lookups cheap:

- **Read a line range, not a file.** `sed -n 'a,bp'` for the spec and
  the architecture document — both are over a thousand lines and a
  task file cites the range.
- **Hand a sweep to the `researcher` agent.** Anything that would open
  more than five files, or one file over ~400 lines (a CI log, a task
  file's full history), goes to `.claude/agents/researcher.md` and
  comes back as a conclusion with `path:line` evidence.
- **A tool result over a screen goes to a file.** 60 lines is the
  budget. A log, a job listing or a persisted read is written to the
  scratchpad and read back by `head`, `grep` or the tool's own
  `tail_lines` — never taken whole. `UX-711`: a result that enters the
  live context is re-bought at every rebuild (`UX-707`), and round 94
  attributed 26k tokens to one job-log read over five calls.
- **Trust the guards' names.** `tests/unit/` is one file per claim,
  named for the claim; `ls tests/unit | grep <word>` is usually the
  fastest answer to "is this held?".
