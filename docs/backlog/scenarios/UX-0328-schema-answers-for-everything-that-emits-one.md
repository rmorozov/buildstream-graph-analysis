# UX-328: --schema answers for everything that emits one

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-190 (the contract discipline), UX-230/UX-234 (the emitters that outgrew it) | **Serves:** R1; every payload consumer | **Topic:** contracts

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

## Outcome (round 48, 2026-08-27) — 🟢 Done

### The gap, measured

```text
$ bga whatif tests/fixtures/golden/mixed_task_kinds --format json | head -2
{
  "schema": "whatif/v1",
$ bga whatif --schema
Error: `--schema` is available on analyze, blast, compare, correlate,
diagnostics, floors, graph, replay, sweep, utilisation;
whatif produces no versioned JSON output.
```

The refusal is falsified by the tool's own output two lines up, and
`store/v1` and `store-aggregate/v1` were in the same state:

```text
contracts.printable()   7   analyze/v2 blast/v1 compare/v1 correlate/v1
                            store-aggregate/v1 store/v1 whatif/v1
answerable by --schema  4   of those 7 (whatif, store, store-aggregate
                            printable and unenrolled)
```

### After

```text
$ bga whatif --schema            -> whatif/v1's contract
$ bga snapshot --list --schema   -> "bga snapshot --list --format json"
$ bga snapshot --aggregate --schema
                                 -> "bga snapshot --aggregate --format json"
$ bga snapshot --schema
Error: ...
  `bga snapshot` prints a document only with `--aggregate`, `--list`;
  without one it writes a run directory and prints a report.
```

`snapshot` is **one command and two documents**, so a
command → id mapping cannot answer it. The flag selects, and the
mapping is consulted flag-first: answering `--aggregate --schema` with
`store/v1` would be a confident wrong answer where the old behaviour
was merely a missing one.

### The fourth defect, which the filing did not have

Enrolling three turned up a fourth, and it is the same class one turn
worse. **`bga sweep --schema` printed `analyze/v2`.** Its document:

```text
sweep's keys      calibration_capacities, capacity_model_caveat,
                  knee_points, monotonicity_violations, resource, sweeps
analyze/v2 needs  schema, run_id, total_duration_us, section
present           0 of 4
```

Not "a different shape" - **none** of the required keys, and no
`schema:` key at all. A missing answer sends a reader to look; a
confidently wrong one sends them to write a parser against a shape
that does not exist.

De-enrolled, with `_EMITS_NO_CONTRACT` carrying what it emits instead
so the refusal is a description rather than a shrug, and the contract
the document wants filed as **`UX-339`**. Two clauses hold the
absence, so it cannot drift back and cannot quietly acquire an id
without the enrolment following.

### Why the guard is structural

A list of enrolled commands is exactly what fell behind - three
emitters were added and the list was not - so a second list would have
the same lifetime. Both sides are derived instead:

- **emitted**: each command run over a fixture, the id read out of its
  own stdout;
- **answerable**: `bga <cmd> [flag] --schema` really run;
- **file-written**: declared with the file each lives in, which is the
  one legitimate reason for an id to have no command.

Their union is asserted equal to `bga.contracts`' inventory, which is
derived from the package. A new emitter either answers `--schema`, or
is declared file-written, or the union stops matching.

`docs/README.md`'s three claims are now derived from that inventory
rather than restated: the row count, the invocation form, and which
ids `--schema` does not know.

### Mutations verified red and reverted (6)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | strip `whatif`'s enrolment (the filing's own mutation) | 2: the per-command equality, and the union |
| M2 | `snapshot --aggregate` answers with `store/v1` | 2: the per-flag clause, and the union |
| M3 | `sweep` re-enrolled as `analyze/v2` | 1: `schema_refuses_rather_than_guessing[sweep]` |
| M4 | the document claims "Nine ids" again | 1 |
| M5 | the document promises `bga --schema <id>` again | 1 |
| M6 | `sources/v1` dropped from the file-written declaration | 2: the union, and the "last four" sentence |

M1 and M2 both reddening the *union* as well as their own clause is
the structural half working: the specific clause says which command,
the union says the inventory no longer adds up, and either alone
would be a weaker guard.

### Deviation from the Required Fix

- The Required Fix names three commands to enrol. A fourth,
  `sweep`, is **de-enrolled** instead - the opposite direction, for
  the same reason. Recorded rather than folded in silently, and the
  contract it needs is filed as `UX-339` rather than invented here.
- `docs/README.md` keeps the `bga --schema <id>` *form* nowhere, per
  Out of Scope, but the tool now answers a contract id with the
  command that prints it (`"\`analyze/v2\` is a contract id, not a
  command. Ask the command that emits it: \`bga analyze --schema\`."`).
  That is not the dispatcher the item declined - it is the same class
  of false refusal this item was filed for, one level up, and it cost
  four lines.
