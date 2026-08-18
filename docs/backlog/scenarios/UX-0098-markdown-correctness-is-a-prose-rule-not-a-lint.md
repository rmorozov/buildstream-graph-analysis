# UX-98: markdown correctness is a prose rule, not a lint

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** —

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

---

## Resolution (round 12)

**Status:** 🟢 Done

### The measurement changed the answer

The Required Fix says to decide between PyMarkdown and
`markdownlint-cli2` **by measuring both against the five real defects**,
and names the must-catch criterion: *inconsistent cells-per-row, with
the `\|` escape understood*.

PyMarkdown catches **none** of it. Reconstructed the round-11 defect
exactly — a 6-column header with a row quoting a jq pipeline — and:

```text
$ python3 -m pymarkdown scan unescaped-pipe.md
unescaped-pipe.md:5:1: MD013: Line length [Expected: 80, Actual: 95]
```

Line length, which this task says to disable, and nothing else. The
single-cell caption row produced no finding at all. The reason is
structural rather than a configuration mistake: **PyMarkdown implements
MD001–MD048**, and the table rules are markdownlint v0.34+ additions —
`MD055` (table pipe style) and `MD056` (table column count) have no
PyMarkdown equivalent:

```text
$ python3 -m pymarkdown plugins list | grep -oE '^  md[0-9]+' | sort | tail -1
  md048
```

So the preferred tool cannot meet the criterion, and the named fallback
needs a Node toolchain the task explicitly rules out.

### What shipped instead: both halves, each where it belongs

**The table check is ours**, in
`tests/unit/test_docs_links_and_commands.py` — about 40 lines, no
dependency at all, and it understands what a renderer understands:
`\|` does not split a cell, leading and trailing pipes are delimiters,
fenced code blocks are not tables, and a *contiguous run* of rows is one
table (two tables of different widths in one file are normal — the first
draft got this wrong and failed on every document).

**PyMarkdown still earns its place** for the rest of the correctness
class and is wired as `make lint-docs`, called from `make lint`, with
`.pymarkdown.json` giving a one-line reason for every disabled rule. It
found 11 real pre-existing findings, all in `README.md` (fenced blocks
with no language, two fences without surrounding blank lines); all
fixed.

### It found a sixth defect immediately — one written an hour earlier

The round-11 sweep found five. The test found a sixth on its first run:

```text
docs/backlog/scenarios/README.md:116: 7 cells against a 6-cell header
```

That row is `UX-97`'s own status text, committed about an hour before,
describing the `pytest | tee` bug — with the pipe unescaped. The defect
class recurred *inside the commit that fixed the last instance of it*,
which is the entire argument of this task, demonstrated without being
asked for.

### Acceptance

- Both defect shapes re-introduced one at a time on a scratch copy:
  **CAUGHT**, each naming file and line.
- Clean tree: `make lint-docs` and `make lint` pass; suite 1241.
- `pip install -e ".[dev]"` is sufficient — `pymarkdownlnt` is in that
  extra, no toolchain outside the Python one CI already has, so CI's
  existing `Lint` step runs it with no workflow change.
- `make lint-docs` exits 2 on an injected unclosed fence.

### Deviation, recorded

Required Fix item 1 says "pick and integrate a markdown linter… the
linter must catch all five". No pip-installable linter does. The rule is
enforced as specified; the mechanism is split because the tooling forced
it, and the half that matters most is the half no linter offered.
