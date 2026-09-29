# UX-1118: nothing formats the code, so layout is argued in review

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29); Ruslan took it on the audit thread (2026-09-29 06:09) | **Serves:** the implementing session and every reviewer | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** none — named test_the_tree_is_formatted.py, absent from tests/

## Motivation

`ruff format --check bga tools tests`: **839 of 852 files would change**;
no `[tool.ruff.format]`, no black. Layout is held by nobody, so it arrives as
review comments and as `W293` (626 hits under `--select W`). The audit's
style-guide answer is PEP 8 as a formatter enforces it, not as a document.

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     `[tool.ruff.format]` quote-style "preserve" (line length 120 inherited). Commit A: the block, `python3 -m ruff format bga tools tests .claude/hooks`, the ledgers re-adopted, one forced guard rewrite. Commit B: .git-blame-ignore-revs (A's sha), `python3 -m ruff format --check` in lint-code, `ruff format` in the edit hook, the guard. Lands last, alone, on the merged tree
Rejected:  quote-style double (850 files, baseline churn 140, 7 fast-tier reds vs preserve's 842, 124, 1); one commit (B names A's sha); `--write --force` for the baseline (labels 124 old findings as a new forced batch)
Files:     pyproject.toml; every reformatted .py (842 measured); tests/quality_baseline.json; tests/quality_reference.json; tools/dev_baseline.py (`--rekey`); tests/unit/test_the_ranking_orders_equals.py (text grep -> AST call check); .git-blame-ignore-revs; Makefile; .claude/hooks/lint-edited-python.sh; tests/unit/test_the_tree_is_formatted.py
Guard:     format --check clean and the ignore-revs sha resolves; `--rekey` accepts only equal (tool, rule, file) multisets and rewrites findings and forced batches in nth order
Mutation:  re-indent one function by hand - reddens; rekey with one extra finding - refuses (drop the multiset check and that test reddens)
Class:     bookkeeping (cap lifted). Measured: 124 new/124 stale identities with equal multisets; 174 grown size cells, adopted with an AST-equality check per file pasted in the Outcome
Split:     last, after every other track; opus
```

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
