# UX-109: the docs lint scans two files and reads as though it scans `docs/`

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-98 (done)

> Filed as `UX-105` and renumbered to `UX-109`: Direction 4's
> `UX-105`-`UX-108` landed on `main` first. The commit that filed this
> one still says "UX-105" in its subject line, which is why this note is
> here rather than left to whoever finds the mismatch.

## Motivation

`make lint-docs` runs:

```makefile
python3 -m pymarkdown --config .pymarkdown.json scan README.md docs/
```

PyMarkdown's `scan` does not recurse without `-r`. Measured on the
current tree, that command scans exactly two files:

```console
$ python3 -m pymarkdown --config .pymarkdown.json scan docs/ ; echo "exit=$?"
exit=0
$ ls docs/*.md
docs/README.md
```

Every other document — `docs/spec/`, `docs/guides/`, `docs/design/`,
`docs/contributing/`, `docs/audits/`, and all 104 files under
`docs/backlog/` — is unlinted, and the target's name and the `docs/`
argument both say otherwise. With `-r` the same configuration reports
**1300 violations**:

| rule | count | what it is |
|---|---|---|
| MD022 | 537 | headings not surrounded by blank lines |
| MD040 | 336 | fenced block with no language |
| MD032 | 277 | lists not surrounded by blank lines |
| MD031 | 140 | fences not surrounded by blank lines |
| MD001, MD038, MD014, MD011 | 10 | heading increment, spaced code span, `$` in a shell block, reversed link |

This is the same defect shape as `UX-84` (a whole test tier gated on a
binary CI did not have, so it was skipped everywhere and read as
passing) and as `UX-97` (a count grep anchored at a column the output
never used). A gate that cannot fail is worse than no gate, because the
repository is written as though it holds.

Found while adding a document during `UX-93`: `make lint` passed, and a
direct scan of `docs/backlog/scenarios/` on the same config immediately
reported MD040 on three files.

## Required Fix

1. `make lint-docs` scans the tree it claims to (`-r`, or an explicit
   file list generated from the tree).
2. Bring the tree to whatever rule set is then enforced. Two honest
   routes and the choice must be recorded, not defaulted into:
   - fix all 1300 (they are mechanical: blank lines and fence
     languages), or
   - disable the rules that this project deliberately does not follow,
     with the same one-line reason per rule that `.pymarkdown.json`
     already carries for its other 17 disables.
3. A test that the lint target's scope is the whole tree, so this cannot
   silently narrow again — the same reasoning that made `UX-97` pin a
   count rather than assert `> 0`.

## Out of Scope

- The five defect classes `UX-98` enforces in
  `tests/unit/test_docs_links_and_commands.py` (table cell counts, split
  tables, link resolution): those already scan every document and are
  unaffected.

## Acceptance Test

- `make lint-docs` reports a violation injected into a document under
  `docs/spec/` (today it reports nothing).
- Clean tree: `make lint` passes.
- The scope test fails when the target is reverted to a non-recursive
  scan.

---

## Fix Implemented

`make lint-docs` recurses (`scan -r`), and the tree it now scans is
clean.

### The choice the Required Fix asked to be recorded

Route 1 for 1287 of the 1300, route 2 for the remaining 13.

**Fixed (1287)** — the class `.pymarkdown.json` says it enables, *"the
class that changes how a document renders"*: blank lines around
headings, lists and fences (MD022, MD031, MD032), and a language on
every fence (MD040). Applied by a fixer that only ever inserts a blank
line or adds `text` to a bare fence, tracks fenced state so nothing
inside a code block is touched, and rewrites no prose. 176 files.
PyMarkdown's own `fix` mode was tried first and is not up to it: it
crashed with a `BadPluginError` on `docs/contributing/fixing-guide.md`
and left MD022/MD032/MD040 untouched.

**Disabled with a reason (13, four rules)** — every one is the rule
arguing with content that is correct:

| rule | count | why the content stays |
|---|---|---|
| MD001 | 6 | `docs/spec/specification.md` numbers milestones `# M1` then `### Goal`; editing a contract document's headings for a linter is the wrong trade |
| MD038 | 2 | both quote a literal whose trailing space is part of what is being described (`` `[wrapper][...] INFO: ` ``) — trimming it falsifies the quote |
| MD011 | 1 | fires on a Python subscript, `compute_structural_metrics()['max_depth']`, which is not a reversed link |
| MD014 | 1 | the `$`-prefixed block it flags shows each command's timing on the same line, so the rule's premise (no output shown) is false |

### The guard

`test_the_docs_lint_scans_the_tree_it_names` pins the flag rather than
the behaviour, because here the flag *is* the behaviour. Verified by
mutation both ways: dropping `-r` fails the test, and re-adding it
passes.

And the lint itself, verified by mutation on a document it could not
previously see — removing a blank line before a fence in
`docs/spec/ingestion-pipeline.md`:

```console
$ make lint-docs
docs/spec/ingestion-pipeline.md:9:1: MD031: Fenced code blocks should be
surrounded by blank lines (blanks-around-fences)
make: *** [Makefile:39: lint-docs] Error 1
```

Before this change that same mutation produced silence and exit 0.

Tests: 1 new. Suite: 1323 → 1324.

## Verification Log

Done 2026-08-18. The 1300 figure and the per-rule counts are from
`pymarkdown scan -r` on the tree before the fix; the mutation checks
above were run, not reasoned about.
