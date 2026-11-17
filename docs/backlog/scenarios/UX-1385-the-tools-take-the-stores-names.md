# UX-1385: the tools `bga` dispatches take `@last` and `@prev` too

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-126, UX-134 | **Found by:** a field report, relayed by Ruslan 2026-11-17: "bga extract doesn't support @prev, @last" | **Serves:** R1, R3 | **Topic:** cli | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_run_store.py`

## Motivation

`bga.cli`'s alias pass (`UX-126`) runs over its own parser only. A
dispatched tool parses its own argv, so `bga extract . @last out/` read
`@last` as a file name; five tools had grown their own resolution
(`view`, `timeline`, `snapshot`, `baseline`, `cache-logs`) and six
that read a file every snapshot keeps had none.

## Required Fix

`run_store.resolve_member(token, member)` names one file of the
snapshot an alias resolves to, refusing by name when that capture never
kept it; `resolve_arguments(args, members)` applies it over a
namespace. `bga.cli` resolves through it, and each tool that reads a
snapshot's file declares `SNAPSHOT_ARGUMENTS` and calls
`refuse_unresolved` (exit 2 with the refusal) after parsing:
`extract`, `run-context`, `log-to-chrome` (`build.log`),
`rebuild-set` (`run/graph.json`), `cross-check` (`run/`,
`analyze.json`), `native-to-chrome` (`plane2.log.gz`,
`run/chrome_trace.json`).

## Out of Scope

Output arguments. `wrap`, `capture`, `graph-from-show`,
`gen-synthetic`, `doctor` make a capture rather than read one;
`checkout-cost`'s log is not one a snapshot keeps; `chrome-to-trace`'s
output is the `trace.json` every snapshot holds. Moving the five
existing tool-local resolutions onto `resolve_arguments`.

## Acceptance Test

Container: a `gen-synthetic --store --runs 2` project, each of the six
commands with `@last`/`@prev` at `bc723ded` and on this tree.

## Outcome

**Premise:** held.

### The gap, measured

`gen-synthetic --store --runs 2 --layers 4 --width 5`, `analyze.json`
written into `@last`, at `bc723ded`:

```text
$ bga extract . @last out1
Error: [Errno 2] No such file or directory: '@last'
exit 1
$ bga run-context @last rc.json
Error: Could not find input file '@last'
exit 1
$ bga log-to-chrome @last lc.json
Error: Could not find input file '@last'
exit 2
$ bga rebuild-set @last --cut toolchain.bst --count-only
         ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: '@last'
exit 1
$ bga cross-check @prev @last
         ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: '@last'
exit 1
$ bga native-to-chrome standalone @last n.json
         ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: '@last'
exit 1
```

### The close, measured

```text
$ bga extract . @last out1
Error: Could not find a 'Targets:' line in 'proj/.bga/runs/20260303T091500Z/build.log' - this log doesn't l
exit 1
$ bga run-context @last rc.json
Wrote run-context.json to rc.json
exit 0
$ bga log-to-chrome @last lc.json
Successfully generated trace! Open lc.json in chrome://tracing or ui.perfetto.dev
exit 0
$ bga rebuild-set @last --cut toolchain.bst --count-only
22
exit 0
$ bga cross-check @prev @last
5/8 cross-checks agree
violations reported by bga: 0
exit 1
$ bga native-to-chrome standalone @last n.json
Wrote 44 trace events to n.json
exit 0
```

Every alias reaches its file. `extract` stops at the synthetic log's
missing `Targets:` line (no `bst` here); `cross-check`'s exit 1 is 5/8.

| mutation | reddened | run |
|---|---|---|
| M1 `extract` skips the resolver | extract reaches the file, extract refused by name | 2 failed, 62 passed |
| M2 a missing member is not checked | six of seven refused-by-name cases | 7 failed, 57 passed |
| M3 `load_records` reads plain text | the gzipped raw log a snapshot keeps | 1 failed, 63 passed |
| M4 `cross-check` declares nothing | cross-check takes one snapshot's pair, refused by name, every tool classified | 3 failed, 61 passed |
| M5 a list attribute is skipped | cache-trend list, baseline set | 2 failed, 62 passed |
| M6 `bga.cli` resolves Plane 2 args as runs | every Plane 2 argument, a report alias with no report | 2 failed, 62 passed |
| M7 `log-to-chrome` skips the resolver | converts that snapshot's log, refused by name | 2 failed, 62 passed |
| reverted | — | 64 passed |

### Deviation

`native-to-chrome` could not read `plane2.log.gz` at all:
`load_records` opened it as text while its own refusal names that file
as valid input. `load_records` now opens through `_open_maybe_gzipped`
(`UX-330`'s reader), one line, because the alias names that file.
`log-to-chrome`'s reach is read end to end, not by patching its module:
naming it from `test_run_store.py` took its selection over `HANDFUL`.
