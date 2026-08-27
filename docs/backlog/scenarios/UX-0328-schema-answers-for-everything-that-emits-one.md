# UX-328: --schema answers for everything that emits one

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-190 (the contract discipline), UX-230/UX-234 (the emitters that outgrew it) | **Serves:** R1; every payload consumer | **Topic:** contracts

## Motivation

Stranger walk friction 7, three contradictions in one story:
`bga whatif --schema` refuses with "whatif produces no versioned
JSON output" while `bga whatif --format json` emits
`"schema": "whatif/v1"` two lines up in the same cli.md block;
`store/v1` and `store-aggregate/v1` are likewise emitted but
`--schema`-refused; docs/README.md promises a ``bga --schema <id>``
form that errors (the working form is `bga <cmd> --schema`), says
"Nine ids" above a table of eleven, and claims only "the last
four" are unknown to `--schema` when seven are. The refusal text
is factually false by the tool's own output — the UX-190 rule
outgrown by three emitters nobody re-enrolled.

## Required Fix

Every command that emits a `schema:` id answers `--schema` with
that contract (whatif, snapshot --list, snapshot --aggregate
enrolled); the guard becomes structural — the set of emitted ids
(collected from fixture runs) equals the set of
`--schema`-answerable ids plus the declared run-directory files,
so the next emitter cannot outgrow it; docs/README.md's count,
form and "last four" sentence corrected from the guard's own
inventory.

## Out of Scope

- A global `bga --schema <id>` dispatcher (nice, separate
  decision — the docs stop promising it either way).

## Acceptance Test

The three commands answer `--schema` with their emitted id
(equality); the emitted==answerable guard reds when a new command
emits an unenrolled id (mutation: strip whatif's enrollment →
red); docs/README.md's table count is guard-derived.
