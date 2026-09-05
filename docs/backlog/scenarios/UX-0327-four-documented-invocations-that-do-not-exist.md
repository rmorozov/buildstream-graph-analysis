# UX-327: four documented invocations that do not exist

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-139 (case-study vs instruction rule), the docs-command guard this extends | **Serves:** R1 | **Topic:** docs | **Area:** tools

## Motivation

The stranger walk followed the guides verbatim and hit four
documented invocations the tool refuses (frictions 5, 6, 8, 9):
`bga cache-logs /path/to/project` (README and real-project.md
Step 0a — the positional is actually the **log root**; invoked as
documented it fails on a machine that has that very project's
logs, with an error naming neither the default root nor
`--project`, and printing the unreadable "under .."); `bga
cache-logs . --native-report @last` (cli.md — the flag moved to
`bga correlate --cache-logs` and the docs never followed); `bga
capture census` and `bga capture replay-sandbox` (real-project.md
— `capture` accepts only `{run, report}`); plus the install-mode
contradiction (README says `pip install ./repo`, user mode; cli.md
says `pip install -e .`) and `snapshot --help` citing the
nonexistent `docs/guides/local-loop.md`. The existing docs guard
checks that *command names* exist — flags, subcommands and
positional semantics were never checked, which is exactly where
all four drifted.

## Required Fix

The five doc sites corrected against the real parser; the
cache-logs error message names the default root and `--project`
and loses "under .."; and the guard grows teeth: every `bga …`
invocation in instructional docs (guides + READMEs, not case
studies per UX-139) must parse against the real parser — flags
and subcommands included — so the next moved flag reds the build.

## Out of Scope

- Changing any CLI surface to match the docs (the tool's current
  shapes are the deliberate ones; the docs drifted).

## Acceptance Test

All five sites match the parser; the extended guard passes on the
corrected tree and reds when any instructional invocation gains
an unknown flag/subcommand (mutation: restore `--native-report`
in cli.md → red); the cache-logs misuse error names root and
`--project` (asserted on output).

## Outcome (round 47, 2026-08-27) — 🟢 Done

### Three of the four do exist

Before fixing anything, each named invocation was run. Three of them
work, and worked at `b9f0f66` — **this filing's own commit** — so the
filing is not describing drift that happened after it was written:

```text
$ bga capture census --help
usage: bga capture census [-h] [--json] project_dir            -> exit 0

$ bga capture replay-sandbox --help
usage: bga capture replay-sandbox [-h] [-n N] [--list] …       -> exit 0

$ bga cache-logs --help | grep -c native-report
2                                                              -> the flag is there

$ git show b9f0f66:tools/bst_native_build_tracer.py | grep 'add_parser('
    run_parser     = subparsers.add_parser("run", …)
    report_parser  = subparsers.add_parser("report", …)
    census_parser  = subparsers.add_parser("census", …)
    replay_parser  = subparsers.add_parser("replay-sandbox", …)
```

`bga capture` dispatches on four subcommands, not two, and
`--native-report` never moved off `cache-logs`. The fourth,
`bga cache-logs /path/to/your/project`, produces a good error already —
`UX-127` fixed exactly this and the message names the derived project,
the absolute root it looked in, and what the tree holds instead.

**This is recorded rather than quietly dropped** because a filing that
says four commands do not exist, when three of them do, is the same
class of defect it was filed against — a claim about the tool that the
tool contradicts. What the walk most likely met is a stale install; the
guard below now answers the question mechanically either way.

### What was real

Four things, two of them the filing's and two found by the guard:

| finding | source |
|---|---|
| `bga cache-logs .` in a non-project says "no element logs found under ." and "Nothing to report on." — naming neither the absolute root nor either argument that works | the filing |
| `cli.md`'s Installation section shows `pip install -e .`, the **contributor** mode, while the README teaches user mode — and the difference has shipped three bugs | the filing |
| `bga snapshot --help` cites `docs/guides/local-loop.md`, which does not exist | the filing |
| `bga baseline --help` cites `docs/guides/ci.md` and `bga cache-logs --help` cites `docs/guides/plane3.md` — **neither exists either** | the guard, first run |

Three help strings, not one. The three now name documents that exist
(`real-project.md`, `ci-comment.md`, `cli.md`), and a clause scans every
`docs/…md` path in `bga/` and `tools/` rather than the one that was
reported.

### The guard, and the two things it had to learn

`test_docs_links_and_commands.py` has checked command **names** since
`UX-77`. `tests/unit/test_the_documented_invocations_parse.py` parses
the whole invocation: 88 `bga …` lines inside fences across the guides
and READMEs, each one's flags and subcommands checked against the real
inventory.

Building that inventory is where the work was:

* **Aliases are read by AST, not executed.** A `tools/` alias builds its
  parser inside `main()`, and `UX-326` had just demonstrated what
  running one costs — appending `--help` to a REMAINDER argv started a
  real build inside a unit test. So the flags come from every string
  literal beginning with `-` passed to `add_argument`, and the
  subcommands from every `add_parser("name")`. Read from the source, so
  it cannot drift from it.
* **`--schema` is on no parser at all.** `cli._maybe_print_schema` reads
  it out of `argv` before argparse runs (`UX-190`: it answers about a
  shape, not a run, so it must not need the run directory). The
  inventory adds it from `_SCHEMA_BY_COMMAND` — the same table the hook
  dispatches on — which also means a guide printing `--schema` on a
  command the hook refuses is caught rather than excused. That is
  `UX-328`'s subject, and this guard is where it will show up.

### The cache-logs refusal

```text
before:  Error: no element logs found under .
           Nothing to report on.

after:   Error: no element logs found under /tmp/…/emptyd
           The default log root is /root/.cache/buildstream/logs; this was pointed somewhere else.
           Hand it the project directory instead - `bga cache-logs PROJECT_DIR` reads `name:` out of
           its project.conf and resolves the log tree itself - or name the project with `--project NAME`.
           `bga cache-logs --list` shows every project the tree holds, with counts and spans.
```

Absolute, because "under ." names a directory only the reader can
resolve and reads as a truncation. `UX-127`'s better message for a
project directory is untouched, and a clause holds that too — the fix
had to be a second branch, not a replacement.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| Z1 | restore `--native-report` on a `bga correlate` line in `cli.md` — the filing's own suggested mutation, moved to a command that really lacks the flag | the no-such-flag clause |
| Z2 | restore `bga capture profile` (a subcommand that does not exist) in a guide | the no-such-subcommand clause |
| Z3 | point a help string back at `docs/guides/local-loop.md` | the help-cites-what-exists clause |
| Z4 | restore "Nothing to report on." | the names-the-two-ways-out clause; the project-shaped clause stayed green |

### Deviation from the Required Fix

- "The five doc sites corrected against the real parser" — three of the
  five were already correct, and the correction is recorded above rather
  than performed. Two others were corrected, and **two more the filing
  did not know about** were found by the guard.
- The guard checks flags and subcommands, not positional *counts*:
  several commands take optional positionals and a guide legitimately
  shows the short form. Argument values are not checked either — a path
  in a guide is illustrative. Both limits are written into the guard's
  own docstring rather than left implicit.
