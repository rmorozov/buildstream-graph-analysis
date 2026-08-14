# P4-04: Add basic Python linting

**Priority:** P4 | **Status:** 🔴 Not Started | **Depends on:** none

## Spec Reference
Not spec-mandated - code-quality tooling.

## Current State
`Makefile`'s `lint` target is a literal no-op placeholder (`Makefile:27-28`: `@echo "Linting not yet configured"`). No linter is declared anywhere (`pyproject.toml` has no `[tool.ruff]`/`[tool.flake8]`/`[tool.pylint]` section, no `.flake8`/`setup.cfg`). Nothing currently enforces any style/correctness-lint convention across ~30+ modules and ~35 test files.

## Required Fix
1. Pick one tool - `ruff` is the pragmatic default (single fast binary, covers pyflakes-equivalent correctness checks + import sorting + a good chunk of pycodestyle in one pass, no separate isort/flake8-plugin sprawl needed). Add it to `[project.optional-dependencies].dev` in `pyproject.toml` and a `[tool.ruff]` config section.
2. Wire `make lint` to actually run it (replacing the placeholder echo).
3. Start with a deliberately small, high-value rule set (unused imports, undefined names, obvious bugs - `F` codes) rather than a maximal style-enforcement pass on day one; a from-scratch strict config on an existing ~30-module codebase risks either a wall of unrelated noise or blanket-suppressing everything, neither of which is useful. Widen the rule set in a later, separate task once the baseline is clean and the team has opinions on style rules (line length, quote style, etc.).
4. Run it against the current codebase and fix what it finds *that's genuinely a bug or real dead code* (e.g. any leftover unused imports - this session's own P1-15 refactor round found and left some pre-existing ones deliberately alone per its own scope discipline; this task is the natural place to finally clean those up, or explicitly `# noqa` ones kept intentionally, e.g. for interface-stability reasons already documented in the code).

## Out of Scope
- Don't add a formatter (`black`/`ruff format`) or reformat the whole codebase in this task - that's a separate, much larger diff and a separate decision (whether to adopt one at all). File as its own backlog item if wanted.
- Don't add type checking (`mypy`/`pyright`) - separate concern, separate task if wanted (the codebase already uses type hints throughout, so this would be a reasonable, well-scoped follow-up).

## Acceptance Test
`make lint` runs a real linter, exits 0 on the current (cleaned-up) codebase, and exits non-zero when a deliberately-introduced unused import or undefined name is added (verify this, don't just assume the config works).

## Verification Log
_(append real command + output here once run, before marking 🟢)_
