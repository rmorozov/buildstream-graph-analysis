# UX-327: four documented invocations that do not exist

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-139 (case-study vs instruction rule), the docs-command guard this extends | **Serves:** R1 | **Topic:** docs

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
