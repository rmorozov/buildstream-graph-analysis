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

## Outcome

**Gap measured:** `grep -rln "bga-foundation" docs/guides README.md
docs/design/capture-workflow.md` → nothing, before this change.

**Close measured:** `grep -c bga-foundation docs/guides/*.md` →
`cli.md:2`, all others `0`. `python3 -m pytest
tests/unit/test_docs_links_and_commands.py -q` → `58 passed`.
`python3 -m pytest tests/unit/test_a_pasted_guide_block_is_fresh_or_dated.py
-q` → `29 passed` (the new ````bash`/`jq` block is not diffed against a
fresh run — it is not a bare `$ bga …` fence — but was run for real and
its pasted JSON matches byte for byte). `PYTHONPATH=<worktree> python3
-c "...from bga.cli import main..." analyze
tests/fixtures/foundation_declared/run --diagnostics --format json |
jq -c '{top_fan_in: .elements.top_fan_in, fan_in_findings: [...]}'` →
`{"top_fan_in":[],"fan_in_findings":["fan-in-foundation"]}`; with the
fixture's own `"foundation": ["sink.bst"]` key removed on a copy →
`{"top_fan_in":["sink.bst"],"fan_in_findings":["fan-in-ranking"]}`.
`python3 tools/dev_touching.py --base 3afade2e` → `55 file(s) selected
… 1646 passed, 5 skipped`. `make lint` → clean (baseline noise only).
`bga snapshot --help` now names `bga-foundation` in one sentence and
points at the guide section; `PYTHONPATH=<worktree> python3 -c
"...from bga.cli import main..." snapshot --help | wc -l` → `47`
(`tests/unit/test_help_is_short.py`'s `CAP = 47`). `python3 -m pytest
tests/unit/test_help_is_short.py -q` → `103 passed`.

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| `docs/design/capture-workflow.md`'s link target `../guides/cli.md` → `../guides/cli-BROKEN.md` | `test_every_relative_documentation_link_resolves` | 1 failed |

Restored from a saved copy (`diff` against the copy → identical), then
`test_every_relative_documentation_link_resolves` → `1 passed`.
`cli.md`'s own `[declare or dismiss](#declaring-a-foundation-tier-ux-683)`
link is a bare `#anchor` reference, which every link guard in this file
skips by design (`_links()` strips `#...` targets before checking) —
its only guard is the file-level one above, exercised on the sibling
link into the same heading.

**Verifier hold, addressed:** `bga snapshot --help` has no `epilog=` at
all, only a `description=` (`tools/bga_snapshot.py:27-33`, not
`bga/cli.py`, which only dispatches to it) — the sentence fits
`CAP = 47` regardless, so it was added to `HELP`.

**Not done:** `bga/schemas.py`'s `is_foundation` sentence exists twice,
verbatim, in two different tables (`blast_radius`, `fan_in`) — not the
"one string" the task allowed an edit for — reported as a follow-up
rather than edited.
