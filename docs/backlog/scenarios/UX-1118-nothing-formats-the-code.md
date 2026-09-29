# UX-1118: nothing formats the code, so layout is argued in review

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29); Ruslan took it on the audit thread (2026-09-29 06:09) | **Serves:** the implementing session and every reviewer | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

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

## Outcome

**Gap measured.** On `939947cf`: `python3 -m ruff format --check bga tools
tests .claude/hooks` (ruff 0.16.8) -> `867 files would be reformatted, 13
files already formatted`; with `quote-style = "preserve"` -> `859 files would
be reformatted, 21 files already formatted` (the Decision's 842 was an older
tree).

**Close measured.** Commit A (`6e2043a6`): `859 files reformatted`. Per file,
`ast.dump` of `HEAD~` vs A: 816 identical, 39 equal once docstring lines are
stripped (ruff re-indents docstrings), 4 differ - the four deviations below.
`dev_baseline.py --rekey`: `rekeyed 128 identities; 600 finding(s)`, every
forced batch's size unchanged; `--check` -> `clean: 600 finding(s)`.
`dev_sizes.py --adopt --force`: `wrote 161 file(s) ... (253 cell(s)
changed)`, 175 grown. Commit B: `ruff format --check` -> `881 files already
formatted`, exit 0; in `make lint-code`; the edit hook formats before it
lints. `git blame -s bga/sources.py`: 98 lines on A; with
`--ignore-revs-file .git-blame-ignore-revs`: 7.

| Mutation | Reddened | Count |
|---|---|---|
| `bga/sources.py` `is_building_kind` body re-indented by hand | `test_the_tree_is_formatted` | 1 failed, 4 passed |
| multiset check dropped from `rekey_pairs` | `test_an_extra_finding_is_refused_and_nothing_is_written` | 1 failed, 4 passed |
| stale paired by `sort_key`, not HEAD's row | `test_pairs_follow_the_source_order_not_the_text` | 1 failed, 4 passed |
| ignore-revs sha -> `000...01` | `test_the_ignore_revs_name_commits_that_exist` | 1 failed, 4 passed |
| `compute_blast_radius` passes `list(results)` | `test_compute_blast_radius_uses_this_function` (AST) | 1 failed, 5 passed |

**Deviation.** A is not format-only in four files: the format turned two
docstrings opening on a quote into `""" "...`, which raised two new `D210`
findings `--rekey` refused (130 new vs 128 stale), so `bga/sources.py`
`format_kind_split` and `tools/bst_native_build_tracer.py` `classify_binary`
docstrings were reworded (AST equal with docstrings blanked);
`tools/dev_baseline.py` gained `--rekey`, with `head_document`'s git read
split into `head_text` so the rekey adds no `S603`/`S607`;
`test_the_ranking_orders_equals.py` became the AST call check. The rekey
guards live in `test_the_tree_is_formatted.py`, not a file of their own.
