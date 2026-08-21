# UX-183: progress you can see, pipes that stay clean

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-159 (the phase lines this refines), UX-168/UX-169 (the long analyses this narrates)

## Motivation

Field feedback, first deployment on big captures: *"some bga commands
can take considerable time... progress bar and progression status
messages would be great — but it definitely can break some scenarios
with passing tool output into something through unix pipe."* Both
halves are the requirement. UX-159's phase lines say *which* step is
running; on a big capture a step can hold one line for minutes
("Analyzing the captured trace..." over a 200k-process trace), and
silence-within-a-phase is the old problem one level down.

The pipe half is already policy-shaped: report output goes to stdout,
phase lines to stderr — so the design space is exactly "what may
stderr do, and when".

## Required Fix

1. **In-phase progress on stderr, only when stderr is a TTY**
   (`os.isatty(2)`): a single self-overwriting line
   (`\r  parsing trace: 120k/480k lines`), updated at most a few times
   a second, cleared before the next real line. Not a bar library —
   one carriage-return line, no dependencies.
2. **When stderr is not a TTY**: exactly today's behavior — the phase
   lines, nothing else. No `\r`, no partial lines, ever, in a log
   file or a pipe.
3. **stdout is untouched in both modes** — a guard asserts the bytes
   on stdout for `--format json` paths are byte-identical with the
   progress on and off (the pipe scenario the user named, made a
   test).
4. Progress points where minutes live: trace parse (line count is
   knowable from a first cheap pass or file size ratio), pairing,
   extraction's `bst show`, census walk, store size walk. Each phase
   already announces itself; this adds the moving number inside the
   long ones.
5. `BGA_NO_PROGRESS=1` (and `--no-progress` on snapshot) for the TTY
   user who wants stillness — cheap, and it makes the TTY path
   testable without a pty.

## Out of Scope

- Progress for `bst`'s own build (bst streams its own; UX-159 settled
  this).
- Any change to what stdout carries.

## Acceptance Test

Under a pty harness (or with the env forced), the progress line
appears and is cleared; with stderr piped to a file, the file contains
only whole phase lines (asserted byte-exactly against today's);
`bga analyze --format json | jq .` works unchanged with progress
forced on (the user's pipe scenario, verbatim). Mutation: writing
progress unconditionally reddens the piped-stderr assertion.
