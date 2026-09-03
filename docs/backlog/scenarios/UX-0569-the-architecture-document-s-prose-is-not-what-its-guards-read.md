# UX-569: the architecture document's prose is not what its guards read

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-233 (the contracts guard), UX-472 (the last prose drift filed here) | **Serves:** the reader who opens architecture.md to price a change | **Topic:** docs

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

## Outcome

**The gap, re-measured.** Two of the Motivation's four lines were stale
or wrong:

```text
$ git ls-files docs/backlog/scenarios | wc -l   # the Motivation said 560
591
$ git ls-files docs/backlog/tasks | wc -l       # line 3's other figure
75                                              # right, and never checked
$ for n in bwrap_shim.py trackevent.py hook.c spine.c dev_run.sh; do \
    printf '%-16s %s\n' "$n" "$(grep -c -- "$n" docs/design/architecture.md)"; done
bwrap_shim.py    0     trackevent.py    5
hook.c           3     spine.c          2     dev_run.sh       0
```

So "0 hits" held for `bwrap_shim.py` and `dev_run.sh` only; the other
three were in the prose and the verification log, but not in the `tools/`
map. The reading-order line held exactly as filed - neither
`optimization-walkthrough-06.md` nor `design-directions.md` is tracked.

**The backticked-name population, measured before the clause was
written** (36 tracked `.md` outside `docs/backlog/` and `docs/audits/`):

```text
212 backticked `*.md` spans, 88 distinct names
    105 repo-root paths   80 beside the document   23 bare basenames
      0 inside a code fence
      4 resolve to nothing: architecture.md:1021 (2, fixed here) and
        style-guide.md:48,172 (2, exempted - a split document's old
        name and a filename-form illustration)
```

**The close.**

```text
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py \
      tests/unit/test_a_counted_figure_is_derived.py -q
75 passed in 17.38s
$ make test-touching
27 file(s) selected · 575 passed, 3 skipped in 25.82s
$ make lint
All checks passed!
```

**Mutations.**

| mutation | what reddened | count |
|---|---|---|
| line 3: `591` -> `75` | `test_the_count_is_the_directory[scenarios]` | 1 failed, 3 passed |
| line 3: tasks `75` -> `74` | `test_the_count_is_the_directory[tasks]` | 1 failed, 3 passed |
| `_backlog_files` reads `{directory}X/` | both count clauses **and** both population clauses | 4 failed |
| `` `nowhere.md` `` into architecture.md:1039 | `test_every_backticked_markdown_name_resolves` | 1 failed, 43 passed |
| `_MD_NAME` matches nothing | `test_the_code_span_sweep_reads_a_population` (the resolve clause passed vacuously - what the floor is for) | 1 failed, 1 passed |
| a bogus `_NOT_A_FILE` entry | `test_every_exempt_name_is_still_written` | 1 failed, 43 deselected |
| drop `tools/bga_snapshot.py` from the bullet | `test_the_architecture_names_the_file_behind_each_command` | 1 failed, 43 deselected |
| drop `tools/native_trace/bwrap_shim.py` | `test_the_architecture_lists_every_native_trace_member` | 1 failed, 43 deselected |

The `nowhere.md` mutation left the pre-existing
`test_every_relative_documentation_link_resolves` green, which is the
evidence that the new clause is what holds it.

**A guard that did not discriminate, and was replaced.** The entry-point
map was first written as a fenced ```` ```text ```` block. `UX-579`'s
`test_the_documented_bga_lines_parse` reads every fenced line beginning
`bga ` as a command and refused three of them ("No closing quotation",
from `Plane 1's capture`). The map is now a bullet list, which also
keeps its rows out of `test_the_command_table_is_the_cli`'s
`^\| \`bga ` scan.

**Deviation from the Required Fix.**

- The count sentence is derived against **591**, the whole tracked
  directory - the population the Motivation's own `ls | wc -l` names.
  It grows on every filing, so this guard reds on the next one - the
  `UX-549` shape working as specified, and worth its own item.
- `tools/dev_run.sh` is named in the Motivation's last line but not in
  the Required Fix, and is not a plane's entry point. Left out.
- `docs/contributing/style-guide.md`'s two deliberate non-files are
  exempted rather than edited: another track owns that file this round.
