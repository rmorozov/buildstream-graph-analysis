# UX-1112: the push gate re-lints ten megabytes of markdown the diff never touched

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** the implementing session, which pays the push gate on every push | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** none — named test_the_push_gate_lints_what_changed.py, absent from tests/

## Motivation

`make lint-docs` scans 1,303 tracked markdown files (10.6 MB) on every
`make lint`, `make test` and `make push-check`. On a 4-core container:
**154 s** single-process; `docs/backlog/scenarios/closed.md` (729 KB) alone
**96 s**; `xargs -P4 -n80` 111 s, because the one file dominates. `make
push-check` measured 2m46s end to end, most of it this scan.

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     new tools/dev_lint_docs.py prints the NUL-separated markdown list: no argument = today's `git ls-files` pathspecs (lint-docs unchanged, UX-509); `--base REV` intersects with `git diff --name-only -z --diff-filter=ACMR REV -- <pathspecs>` (rename keeps the new path, delete drops, untracked dropped); full list when `.pymarkdown.json` changed or REV does not resolve. push-check runs `--base "$base" | xargs -0 -r python3 -m pymarkdown ... scan`
Rejected:  inline shell in the Makefile (pathspecs twice, untested); dev_touching.py (maps a diff to tests); untracked .md (breaks UX-509)
Files:     tools/dev_lint_docs.py; Makefile (`lint-code` holds ruff + baseline; `lint: lint-docs lint-code`; `push-check: records lint-code` plus the changed-docs line); tests/unit/test_the_push_gate_lints_what_changed.py
Guard:     scratch repo: broken-unchanged + clean-changed is green; swapped reds; touching .pymarkdown.json reds; a rename lints the new name; a delete does not error. test_docs_links_and_commands.py::test_the_docs_lint_scans_the_tree_it_names keeps `make lint` full
Mutation:  `--base` returns every file - first case reddens; lint-docs passes `--base HEAD` - the UX-109 guard reddens
Class:     optimization - push-check measured 2m46s, lint-docs 154 s of it
Split:     B track, after 1113 (shared Makefile lines); run test_a_docs_only_diff_runs_its_guards.py
```

## Required Fix

`push-check` lints only the markdown changed against the merge-base (the
same base `dev_touching.py --base` already takes); `make lint` and CI keep
the full scan, once. A diff touching `.pymarkdown.json` lints everything.

## Out of Scope

Splitting `closed.md` (a separate row if the full scan still hurts).

## Acceptance Test

`tests/unit/test_the_push_gate_lints_what_changed.py`: a scratch repo with
two markdown files, one broken and unchanged, one clean and changed —
push-check's docs half is green; flip which is changed and it reds; touch
`.pymarkdown.json` and it reds. Mutation: make the selector return every
file; the first case reddens. The Outcome carries push-check's wall before
and after on one tree.
