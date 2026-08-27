# UX-339: the capacity sweep has no contract

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-328 (which found it), UX-190 (the rule it breaks) | **Serves:** R5 — capacity operators, and every payload consumer | **Topic:** contracts

## Motivation

Found while enrolling `UX-328`'s three emitters, and it is the
same defect one turn worse. `bga sweep --format json` prints a
document with **no `schema:` key at all**, and `bga sweep
--schema` answered `analyze/v2` — a contract whose four required
keys the document has **none** of:

```text
sweep's keys      calibration_capacities, capacity_model_caveat,
                  knee_points, monotonicity_violations, resource, sweeps
analyze/v2 needs  schema, run_id, total_duration_us, section
present           0 of 4
```

A missing answer sends a reader to look; a confidently wrong one
sends them to write a parser against a shape that does not exist.

`UX-328` de-enrolled it, so the tool now says what is true — *"that
document carries no schema id yet"* — and the guard holds the
absence rather than letting it drift back. That is the honest
stopgap, not the fix: `bga sweep` is `R5`'s command, its output is
the capacity answer, and it is the one document in the tool a
consumer cannot version-check.

## Required Fix

`sweep/v1`: the document declares its id like every other, with
`schemas.py` carrying the types, units and view-hints — the
`resource` it swept, each capacity's makespan and normalized
improvement, the knee points, the monotonicity violations, and the
calibration the projection used (which is the part a reader most
needs qualified). `bga sweep --schema` enrols and answers with it.
`UX-328`'s emitted==answerable guard then covers `sweep` by
existing, and `NO_CONTRACT` in that guard empties — the guard
already reddens if this lands without the enrolment, which is why
no new guard is needed here.

## Out of Scope

- Changing what `bga sweep` computes. This is the envelope, not
  the number.
- The viewer drawing it. `store-aggregate/v1` earned a drawing in
  `UX-234` on its own item; this one can too.

## Acceptance Test

`bga sweep --format json | jq -r .schema` is `sweep/v1`; `bga
sweep --schema` prints that contract and `UX-328`'s equality
clause covers it with `NO_CONTRACT` empty; mutation: drop the
enrolment → the emitted==answerable clause reds naming `sweep`.
