# UX-324: a capture that cannot start says so, and leaves nothing

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-125 (doctor's check this reuses), UX-157 (the leaves-nothing rule) | **Serves:** R1 — the first-run experience | **Topic:** capture

## Motivation

Round 45's stranger walk, friction 1: on a machine without `bst`,
`bga snapshot -- bst build all.bst` — the README's own first
command — runs the census happily and then dies in a **30-line
Python traceback** (`FileNotFoundError: ... 'bst'`), while `bga
doctor` on the same machine opens with `[FAIL] bst-present` and a
one-line remedy. Worse, the crash leaves a **debris snapshot**
(`build.log`, `plane2.log`, `capture-context.txt`, no run) —
contradicting the guide's "interrupting before the build starts
leaves nothing behind" — and the debris then poisons later
messages: `--list` describes it as "the build produced no
elements" (the build never started), and `@<stamp-prefix>`
resolution denies it exists while `--list` shows it.

## Required Fix

`snapshot` checks its build command's executable before creating
anything (the doctor check, reused not duplicated) and refuses
with the sentence and the `bga doctor` pointer; nothing is written
on that path. The debris description distinguishes "never started"
from "produced no elements" (the capture context knows which), and
prefix resolution's "Have:" list agrees with `--list` about what
exists.

## Out of Scope

- Debris from mid-build failures (UX-157's salvage rules stand —
  this is only the never-started path).

## Acceptance Test

With a PATH lacking `bst`: snapshot exits with a one-sentence
refusal naming `bga doctor`, exit code documented, and `.bga/runs`
byte-identical before and after (asserted); the traceback is gone
(mutation: bypass the check → the no-debris clause reds). A
never-started debris fixture lists with the honest sentence and
resolves by prefix.
