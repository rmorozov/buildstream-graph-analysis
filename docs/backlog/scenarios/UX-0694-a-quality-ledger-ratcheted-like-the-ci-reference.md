# UX-694: a quality ledger, ratcheted like the CI reference

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-693 (the rule set), UX-418 (the reference method) | **Serves:** the refactor stream, which §6a defines by a measured cost and which has never had one to read | **Topic:** guards

## Motivation

Fixing guide §6a: a refactor is "a measured cost — size, duplication,
a budget", judged by "the measurement moved and no behaviour did".
Nothing writes the cost down, so no refactor has been priced. Round
93 measured it (`radon cc bga tools -s -n C`, an AST pass, `ruff
--select C901,PLR`, `pyright --outputjson`):

```text
functions over McCabe 10           84    (radon C-or-worse: 228 of 1,426 blocks)
maintainability 0.00               bga/correlate.py bga/findings.py bga/report/text.py tools/bst_native_build_tracer.py
longest function                   format_text 548 lines, CC 135     bga/report/text.py:590
                                   create_parser 417 · compute_confidence 401 · build_document 339 · analyze 315
files over 1,000 lines             15   (tracer 6,960 · schemas.py 5,517 · analyzer.py 2,612 · cli.py 2,301)
pyright errors                     270  (mypy 168 in 26 files; 57.5 % of bga/ functions fully annotated)
# noqa                             286  (23 unused)
bandit-class (ruff S)              87
```

## Required Fix

`tools/dev_quality.py` writes `tests/quality_reference.json`: one row
per file — functions over McCabe 10, longest function (lines), file
lines, `# noqa` count, `S` findings, pyright errors, duplicate-code
blocks (`pylint --disable=all --enable=duplicate-code`, the one
duplication measure that is pip-installable). A guard reads the tree
against the reference and fails when any cell **grows**; `--adopt`
rewrites the reference when a cell shrank, in the same commit as the
change that shrank it (the `ci_reference` pattern, `UX-418`). Counts
only — no timing, nothing cross-machine. The ledger's top rows, sorted
by longest function, are the refactor stream's queue (`UX-695`).

## Out of Scope

- A target below today's numbers — the ratchet's direction is the
  policy; the pace is the refactor stream's.
- Test files in the ledger — `UX-690`'s shape budget is the suite's
  ledger; one file, one ledger.

## Acceptance Test

`python tools/dev_quality.py --check` passes on the adopting commit;
mutation: add one branch to a function at exactly 10 — the file's
first cell grows, the guard reddens, `--adopt` refuses to move a cell
upward without `--force`.
