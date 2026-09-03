# UX-569: the architecture document's prose is not what its guards read

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-233 (the contracts guard), UX-472 (the last prose drift filed here) | **Serves:** the reader who opens architecture.md to price a change | **Topic:** docs

## Motivation

Round 82 read every section of `docs/design/architecture.md` against
the tree. The guarded parts hold — the CLI table, the 23-row contract
inventory, the 23 viewer rows, the log's date. The prose between them
does not:

```text
architecture.md:3      "75 docs/backlog/scenarios/ files"      ls | wc -l → 560
architecture.md:1021   reading order names optimization-walkthrough-06.md and design-directions.md
                       ls docs/guides docs/design → neither exists (optimization-walkthrough.md, directions.md)
architecture.md        bst_run_wrapped.py, bst_extract_run.py, bst_cache_logs.py, bga_snapshot.py: 0 hits
                       — the planes' entry points are named only as commands
tools/native_trace/{bwrap_shim.py,trackevent.py,hook.c,spine.c}, tools/dev_run.sh   in neither this map nor §6
```

`test_docs_links_and_commands.py` sees markdown links only, so a
backticked file name that does not exist passes; `UX-88` fixed the
"22 scenario files (there are 76)" count at another line of the same
document, and the count at line 3 kept its 2026-08 value.

## Required Fix

- The two counts derived, not typed — the `UX-549` shape
  (`test_a_counted_figure_is_derived.py`) applied to line 3.
- The link guard extended to backticked `*.md` names: a name in code
  font that ends in `.md` must resolve relative to the document, the
  same rule links obey.
- The planes' entry points named as files where the chapters name
  them as commands, and `tools/native_trace/` listed with its four
  members (`UX-573` gives §6 the same rows).

## Out of Scope

- Rewriting the chapters — the mechanism prose (spine counters,
  trace dictionary, viewer axis) was checked and is true.

## Acceptance Test

Mutation: put a backticked `nowhere.md` in a design document — the
link guard reds; type 75 back into line 3 — the derived-figure guard
reds.
