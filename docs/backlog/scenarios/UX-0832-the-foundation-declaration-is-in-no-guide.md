# UX-832: the foundation declaration is in no guide

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-683 (the tier), UX-684 (the cached-build verdict) | **Found by:** round 115, the design review | **Serves:** R3 whose base runtime leads every ranking | **Topic:** docs | **Area:** bga | **Shape:** mechanical

## Motivation

`UX-683` made foundation a declaration — `variables: {bga-foundation:
"a.bst,b.bst"}` in `project.conf`, read by `bst_extract_run.py:252` —
and a candidates list on the page ("declare or dismiss"). The word
appears in the task file and the tool and in no guide:

```text
$ grep -rln "bga-foundation" docs/guides README.md
(nothing)
```

The owner's base runtime leads "worth optimizing first" on their
project, and by the tree's own rule that is right: nothing was declared,
because nothing told them they could. On the walk capture the leader
(`storm.bst`) is not foundation; the defect is the missing paragraph,
not the ranking.

## Required Fix

A paragraph in `docs/design/capture-workflow.md` and the analysis guide under `docs/guides/`:
what foundation means, the `project.conf` line, what changes on the
page (present, separated, never the top row), and where the candidates
list is. The candidates section links to it. The CLI's `--help` for
`snapshot` names the variable.

## Out of Scope

- Auto-declaring by fan-out — `UX-683` refused it; the owner declares.
- Changing the blast ranking's focus — the ranking is right once the tier is declared.

## Acceptance Test

`grep -c bga-foundation docs/guides/*.md` ≥ 2; `tests/unit/test_docs_links_and_commands.py` green; the candidates section's link resolves; mutation: break the link — red.
