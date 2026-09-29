# UX-1118: nothing formats the code, so layout is argued in review

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29); Ruslan took it on the audit thread (2026-09-29 06:09) | **Serves:** the implementing session and every reviewer | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — named test_the_tree_is_formatted.py, absent from tests/

## Motivation

`ruff format --check bga tools tests`: **839 of 852 files would change**;
no `[tool.ruff.format]`, no black. Layout is held by nobody, so it arrives as
review comments and as `W293` (626 hits under `--select W`). The audit's
style-guide answer is PEP 8 as a formatter enforces it, not as a document.

## Required Fix

`[tool.ruff.format]` in `pyproject.toml` (line length 120, the lint's);
one commit whose diff is `ruff format`'s and nothing else, its sha in a new
`.git-blame-ignore-revs`; `make lint` runs `ruff format --check`, and the
edit hook formats the file it just linted.

## Out of Scope

Any rule-set change beyond formatting; the docstring convention (`UX-1119`).

## Acceptance Test

`tests/unit/test_the_tree_is_formatted.py` runs `python3 -m ruff format
--check` over `bga tools tests .claude/hooks` and asserts the ignore-revs
file names a commit that exists. Mutation: re-indent one function by hand;
it reddens.
