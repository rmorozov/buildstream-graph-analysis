# UX-326: the tool's own sentences are contracts

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-218 (the executed-argv precedent) | **Serves:** R1 | **Topic:** cli

## Motivation

Two frictions from the stranger walk, one rule. (F3) `bga analyze`
ends with a good "Next:" block whose third suggestion prints as
`bga snapshot /abs/path/to/project` — run verbatim it crashes
(`ValueError: command must start with 'bst'`) and deposits debris;
the project belongs in `--project`, and the printer forgot its own
parser. `UX-218` made published `next_steps` argvs *executed* in
tests; this printer is evidently a second, unguarded path. (F4)
`bga compare @prev @last` prints "(--allow-mismatch was given;
treat every figure below with real skepticism)" **with no flags
given** — a sentence asserting a flag state that is false, under
the producer-stamp warning. Both are the same defect: printed
sentences that claim things the program state contradicts.

## Required Fix

Every printed command the tool suggests goes through the one
`next_steps` builder whose argvs are executed against fixtures
(the second printer retired); the `--allow-mismatch` sentence
renders only when the flag was actually passed, and the
mismatch-warning's unconditional text says what is true instead.
A sweep for other flag-claiming sentences rides along, with each
gated on its flag.

## Out of Scope

- New next steps — the block's content is right; only its third
  argv is wrong, and this item fixes the printer, not the plan.

## Acceptance Test

Every command string the CLI prints anywhere (collected by the
guard from captured output on fixtures) parses against the real
parser and the suggested ones execute exit-0 (mutation: re-print
the positional-project form → red); compare without the flag
never prints the flag's name (mutation: unconditional print →
red), and with the flag prints it.
