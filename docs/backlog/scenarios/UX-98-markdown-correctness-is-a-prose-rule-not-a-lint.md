# UX-98: markdown correctness is a prose rule, not a lint

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** —

## Motivation

The round-11 status table rendered broken in GitHub's viewer: the
`UX-75` row quoted a jq pipeline (`.findings[] | select(…) |
.evidence…`) whose two unescaped pipes split a 6-column row into 8
cells — GitHub splits table rows on `|` even inside backtick spans. A
sweep for the same defect found **five malformed rows across three
files** (`docs/backlog/scenarios/README.md`,
`docs/backlog/progress-tracker.md` ×2 with the same unescaped-pipe
cause, and two single-cell caption rows in `UX-69`'s evidence table),
one of them broken since the P-task era. All five are fixed; nothing
stops the sixth.

This repository already knows what to do with a docs failure mode that
recurs: rules 3 and 5 of
[`style-guide.md`](../../contributing/style-guide.md) are enforced by
`tests/unit/test_docs_links_and_commands.py` precisely because prose
rules do not hold. Rule 8 (well-formed markdown) is now written; this
task gives it teeth.

## Required Fix

1. Pick and integrate a markdown linter that runs in this repo's
   existing toolchain. The natural fit is **PyMarkdown**
   (`pymarkdownlnt`) — pip-installable, so it joins the `[dev]` extra
   and the Python-only CI matrix without a Node toolchain;
   `markdownlint-cli2` is the fallback if PyMarkdown's table coverage
   proves insufficient. Decide by measuring both against the five real
   defects above (re-introduce them on a scratch branch): **the linter
   must catch all five**, most importantly inconsistent
   cells-per-row (with the `\|` escape understood).
2. Configure it minimally: enable the correctness class (tables, fence
   closure, heading-level jumps, dangling reference definitions),
   disable pure style opinions (line length, emphasis markers, bare
   URLs) — this repo's docs style is its own and rule-by-rule fights
   with an opinionated default would kill adoption. Every disabled rule
   gets a one-line reason in the config.
3. Wire it as `make lint-docs`, called from `make lint`, and CI runs it
   via the existing lint step. The style guide's rule 8 and editing
   checklist already point at `make lint-docs` by name.
4. First run will surface pre-existing violations across ~120 docs:
   fix the correctness class, add per-file suppressions only where a
   file deliberately shows broken markdown (none known today).

## Out of Scope

- Prose/style linting (sentence length, wording) — rules 1-2, 4, 6-9
  stay human.
- Enforcing the two existing test-backed rules through the linter
  (they are already enforced; moving them is churn).
- Bare-path checking (UX-97 territory).

## Acceptance Test

Re-introduce each of the five round-11 defects one at a time on a
scratch copy (the unescaped jq pipe, one tracker row, one UX-69 caption
row): `make lint-docs` fails on each with a message naming the file and
line. On the clean tree, `make lint-docs` and `make lint` pass, and CI
runs the docs lint (visible in the workflow log). `pip install -e
".[dev]"` is sufficient to run it — no toolchain outside the Python one
CI already has.
