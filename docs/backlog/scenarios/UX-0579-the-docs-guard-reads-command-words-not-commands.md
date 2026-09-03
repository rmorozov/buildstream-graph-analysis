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
