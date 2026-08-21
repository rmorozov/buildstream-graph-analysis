# UX-183: progress you can see, pipes that stay clean

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-159 (the phase lines this refines), UX-168/UX-169 (the long analyses this narrates)

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

## What was built

`bga/progress.py`: a carriage return and a string, with the gate in
front of it. No dependency, no rendering modes, no second thing that
writes to the terminal.

**The gate, in the order it binds.** `stdout` is never touched.
Progress goes to `stderr`, and only when `stderr.isatty()`.
`BGA_NO_PROGRESS=1` turns it off on a terminal too — which is also what
makes the enabled path testable without a pty, and what
`bga snapshot --no-progress` sets.

A `Ticker` is a no-op object when disabled, so a caller writes the same
three lines either way and no phase grows an `if` around its own work.
`step()` counts toward a total when there is one; `note()` draws
elapsed time for a phase with nothing countable in it (a subprocess).
Redraws are throttled to ten a second — on a 200k-event loop a write
per iteration is a cost on the phase it is narrating. The line is
padded to its previous width so a shortening line leaves no tail,
capped at 72 columns so it never wraps (a wrapped `\r` line stops
overwriting itself), erased by `done()` so the phase's own summary
starts on a clean row, and erased by `__exit__` so an exception cannot
leave it drawn. A terminal that disappears mid-phase disables the
ticker rather than raising: progress is decoration, and losing it must
never take the analysis with it.

**The five progress points**, all named in the Required Fix:

| phase | narrates |
|---|---|
| trace parse | `parsing trace: 120000/480000` |
| pairing | `pairing processes: 120000/480000` |
| census walk | `census: 45/90` |
| `bst show` | `bst show: 40s elapsed` |
| store size walk | `measuring the store: 312` |

`bst show` changed shape to get there: it runs through `Popen` with
both streams on temporary files and is polled, rather than
`subprocess.run(capture_output=True)`. That is what makes the wait
pollable at all, and it removes the pipe-buffer deadlock a project with
thousands of elements could otherwise reach with nothing draining
stdout. The pairing ticker counts up rather than toward a total when
its input is `UX-169`'s lazy drain — materialising it for a progress
number would undo the memory work it exists for.

Tests: 21 new
(`tests/unit/test_progress_never_touches_the_pipe.py`). The negative
ones carry the weight: a ticker on a non-TTY writes **zero bytes**; a
redirected stderr holds the phase line and nothing else, with no `\r`
anywhere in it; and the user's own scenario — `bga analyze --format
json` — is run as a subprocess twice, with progress forced on and off,
and the stdout bytes compared. Five mutations, each red, including the
one the acceptance names (writing progress unconditionally reddens the
piped-stderr assertion).

## Deviation from the Required Fix

The acceptance asks for a **pty harness**. The guards drive a stream
that answers `isatty()` instead. The branch under test is
`os.isatty(2)`, a pty adds a Linux-only fixture around the same
decision, and the environment override (item 5, which exists precisely
to make the TTY path testable without one) is exercised on both sides.
The subprocess-level stdout comparison does run through real pipes.

