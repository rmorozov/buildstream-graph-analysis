# UX-151: the arity table is the likeliest field failure, and nothing records the version that breaks it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-146 (the record this extends), UX-11 (the split contract)

## Motivation

The round-15 code review produced the strongest remaining hypothesis
for the Ubuntu 24.04 field failure, and it is testable in one glance at
a diagnostics file. The shim's arity table
(`tools/native_trace/bwrap_shim.py:41-50`) was validated against
bubblewrap **0.9.0** and treats any unknown `--flag` as arity 0. It
omits, among others: `--args`, `--json-status-fd`, `--seccomp`,
`--add-seccomp-fd`, `--argv0`, `--size`, `--perms`, `--chmod`,
`--remount-ro`, `--mqueue`, `--lock-file`, `--bind-fd`, `--ro-bind-fd`,
`--file`, `--bind-data`, the `--overlay*` family, `--userns`,
`--pidns`. Any of those emitted by a newer buildbox-run makes
`split_bwrap_args` stop at the flag's *operand*:
`["--json-status-fd", "12", "--bind", …]` splits to
`opts=["--json-status-fd"]`, `command=["12", "--bind", …]` — the
rewritten argv hands bwrap garbage, bwrap exits non-zero, and the user
sees exactly the field sentence: `buildbox-run failed with returncode
1`, unchanged by `--trace-opens`/`--trace-spine` because the injection
happens regardless.

Two compounding blind spots:

1. **The mis-split detector cannot see this.** The summary flags
   `command[0].startswith("-")`
   (`tools/bst_native_build_tracer.py:3788-3789`) — but the mis-splits
   a post-0.9.0 bwrap actually produces put a *numeric operand* (an fd,
   a size, a mode) at `command[0]`, which starts with a digit. The one
   automated detector for the rewrite breaking misses the shapes most
   likely to occur.
2. **The record omits the fact its own motivation blames.** UX-146's
   file says the table "was validated on bubblewrap 0.9.0" — and then
   the diagnostics record has no `bwrap --version`, no `bst --version`,
   no buildbox-run identity anywhere. The maintainer reading a user's
   JSONL cannot tell which table the argv should be split against.

## Required Fix

1. Widen `_ONE_ARG_FLAGS`/`_TWO_ARG_FLAGS`/`_ZERO_ARG_FLAGS` to the
   current bubblewrap option set (the list above, checked against
   bubblewrap's own `--help` at the version pinned in the fix).
2. An **unknown `--flag` is a recorded, reported condition**, not a
   silent arity-0 guess: the shim notes it in the invocation's JSONL
   line, and the summary counts and names unknown flags seen.
3. Strengthen the mis-split detector beyond `startswith("-")`: flag a
   `command[0]` that is purely numeric, and any `--` token appearing
   *after* the chosen split point.
4. Record an **environment fingerprint** in the diagnostics header:
   `bwrap --version` (from the resolved real bwrap), `bst --version`,
   and the buildbox-run path — once per capture, not per invocation.

## Out of Scope

- Tracking bubblewrap releases forever: item 2 is the structural fix —
  once unknown flags are loud, table drift announces itself.
- The zero-invocation causes (UX-147) and stderr forensics (UX-148).

## Acceptance Test

A synthetic argv containing `--json-status-fd 12` before the command:
the split is correct with the widened table; with the table entry
removed (mutation), the summary reports the unknown flag *and* the
numeric-`command[0]` detector fires. A live capture's diagnostics
header shows the three version fields. The UX-11 split tests still
pass verbatim.
