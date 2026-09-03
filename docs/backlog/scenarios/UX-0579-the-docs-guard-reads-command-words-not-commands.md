# UX-579: the docs guard reads command words, not commands

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-325 (the installed sweep), UX-327 (documented invocations parse) | **Serves:** the next flag rename | **Topic:** guards

## Motivation

`test_docs_links_and_commands.py:573-604` checks that `bga <word>`
names a subcommand or alias — regex `\bbga ([a-z][a-z-]*)` — and
reads no flag; flags are guarded for `blast` only (`:771`). Its scope
excludes `examples/README.md` and `CHANGELOG.md`. Round 82 extracted
63 distinct long flags from the seven guides and every one exists —
by luck, not by guard. The installed sweep runs one hand-chosen argv
per command, not the guides' lines.

## Required Fix

Every fenced `bga …` line in `docs/`, `README.md`, `examples/` and
`CHANGELOG.md` is parsed with the real parser
(`create_parser().parse_known_args` on the tokenised line, run-dir
placeholders substituted), red on an unknown flag or subcommand;
`UX-575`'s piped shape joins the sweep.

## Out of Scope

- Running every documented line — `UX-577` runs the next-step class
  on the committed store; the rest parse.

## Acceptance Test

Mutation: rename a flag in one guide — red naming the line.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** held — the flags were unread, and the sweep found one line
the parser refuses; round 82's "63 flags, all real" was luck, not proof.

### The gap, measured

```text
$ tests/unit/test_docs_links_and_commands.py's regex, on the same lines
\bbga ([a-z][a-z-]*)   -> reads the word, never an argument
$ new sweep, 197 fenced `bga` lines over the swept roots
docs/guides/cli.md:1671: bga correlate RUN_DIRECTORY NATIVE_REPORT.json [-f text|json]
    -> unrecognized: ['[-f', 'text|json]']
```

One line, in a `bash` fence, that a reader can copy and that argparse
refuses: `[-f text|json]` is synopsis notation, not arguments. It is now
two runnable lines. `examples/` and `CHANGELOG.md` contribute **0**
fenced `bga` lines today — they name `bga` only in prose — so their
inclusion buys the next rename, not this one.

### After

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_the_documented_bga_lines_parse.py -q
............                                                             [100%]
12 passed in 2.02s
```

197 lines parsed with `create_parser().parse_known_args`, placeholders
(`RUN`, `RUN/`, `RUN_DIRECTORY`, `/path/to/…`) substituted by a
`tmp_path`. `--schema` is routed to `_schema_for`, not argparse, because
`_maybe_print_schema` answers it before the parser exists (`UX-190`) —
four lines read as drift until that was modelled. Tool aliases keep
their own flags (`UX-67`): the word is checked, not the arguments.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| E | `--format` → `--output-format` in `cli.md:752` | the parse clause, naming `cli.md:752` |
| F | `cache-logs` → `cache-log` in `README.md:269` | the parse clause, naming `README.md:269` |
| G | `UX-575`'s handler re-raises | both piped clauses, 2 of 12 |
| H | `docs/guides` dropped from `SWEPT` | the population clause and the piped clause, 2 of 12 |
| I | `FIXTURE_RUN` → `examples/06-…/.bga/runs` | the tracked-operand clause, 1 of 12 |

The first draft matched `^bga\b`, which `bga/ingest/` satisfies: it read
50 lines of the fixing guide's directory map as commands and reported 55
offenders where there is one. `^bga(\s|$)` is the fix — the same
code-versus-data shape as `UX-403`.

### Deviation from the Required Fix

**Stated narrowing:** `docs/backlog`, `docs/audits` and `docs/spec` are
out of the sweep. They hold 277 of the 474 fenced lines and 41 refusals,
all historic: a task file quoting the command a past round ran is a
record, and the older guard excludes them for that stated reason.
Executing them is narrower still — 4 lines run, the rest parse — because
`examples/**/.bga/runs/` is untracked (`UX-577`) and CI has no store.

```text
$ make test-touching
27 file(s) selected · 583 passed, 4 skipped in 26.75s
$ make lint
All checks passed!
```

<!-- 80 lines, held by test_the_register_is_terse.py::TestOutcomes. -->
