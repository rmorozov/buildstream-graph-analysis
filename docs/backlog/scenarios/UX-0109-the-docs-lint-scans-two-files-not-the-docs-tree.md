# UX-109: the docs lint scans two files and reads as though it scans `docs/`

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-98 (done)

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
