# UX-353: the roles table serves a contract nothing writes

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-341 (one unit per dimension), UX-215 (the element object) | **Serves:** a reader following a role to the payload that answers it | **Topic:** docs

## Motivation

Found by review 5, checklist item 2 - *the review asks whether the
prose around each contract is still true*.

`docs/design/roles.md`'s "bga today" column for R2, the recipe author,
reads:

> **Served.** The element object (`correlate/v1`), blast by resource,
> element history, Plane 2 lanes

`correlate/v1` is superseded. `UX-341` unified the units and moved the
join to `correlate/v2`; `bga.schemas.SUPERSEDED` lists v1 as read,
never written, and every other document says so:

```text
docs/spec/specification.md:1652  | `bga correlate --format json` | `correlate/v2` | ...
docs/design/architecture.md:869  | `correlate/v2` | the two planes joined on element uid ...
docs/design/architecture.md:882  | `correlate/v1` | ... Read, never written | in an older store
docs/README.md:63                | `correlate/v2` | `bga correlate --format json` ...
docs/design/roles.md:40          | R2 | ... The element object (`correlate/v1`) ...
```

The other `correlate/v1` mentions in `docs/` are narrative - round 24
and round 25's audits and `directions.md` recording what was published
when - and a dated record naming the version that existed then is
correct. This one is in a present-tense column headed "bga today",
which is the one place the id has to be the current one: a reader
following the role to the contract lands on a payload the tool has not
written since round 51.

`roles.md` is the only document in `docs/design/` that names a
contract id and is not covered by
`test_the_documents_keep_up_with_the_contracts.py`, which is why the
mechanical half missed it.

## Required Fix

R2 names `correlate/v2`, and the contract-document guard's population
grows to include `roles.md` - the check it already makes for the
architecture and the guides, applied to the one design document that
names an id. What the guard asserts is the property review 5 found
broken: no document outside a dated audit names a `SUPERSEDED` id
except to say it is superseded.

## Out of Scope

- The audit rounds and `directions.md`. A record of what round 25
  published is not a claim about today, and rewriting the id there
  would make the history wrong to make a grep clean.
- Re-examining whether R2 is in fact served. Review 5 checked the
  contract's name, not the role's verdict.

## Acceptance Test

`roles.md` names `correlate/v2`, and a guard fails when any document
under `docs/design/`, `docs/guides/` or `docs/README.md` names a
`SUPERSEDED` contract id outside a sentence that says it is
superseded.

## Outcome (round 54, 2026-08-28) — 🟢 Done

### The gap, and where it was

```text
docs/design/roles.md:40  correlate/v1
  | R2 | **The recipe author** ... | **Served.** The element object
    (`correlate/v1`), blast by resource, element history, Plane 2 lanes |
```

R2 now names `correlate/v2`, and the guard names that line when it does
not.

### The rule is "say so", not "do not mention it"

A superseded id has to be nameable: `architecture.md` and
`docs/README.md` both carry a table of them, and the point of those
rows is to tell a reader holding an old payload that the tool still
reads it. What separates those rows from the roles cell is that they
*say so*. So an occurrence is legitimate when its scope states the
retirement — the vocabulary the documents already use, three phrases,
kept short deliberately: a marker set that grows to fit whatever a
document happens to say has stopped being a check.

**Scope is the row for a table, the paragraph for prose.** Both halves
were bought by a mutation:

- `docs/README.md`'s sentence about the retired set names `analyze/v3`
  on its own line and states the retirement two lines above. Line
  scope would have flagged it; paragraph scope is where a reader takes
  it from.
- The architecture's contracts table is **one block of thirty rows**.
  Block scope let one row's "never written" license every id in the
  table, and Q3 — dropping the marker from `correlate/v1`'s own row —
  changed nothing. A table row answers for itself now.

`directions.md` is exempt, and the exemption is conditional rather
than a name on a list: the file opens by calling itself an argument
about direction and pointing at `architecture.md` *"for what the tool
is today"*, and a clause holds it to that sentence. Two more clauses
guard the instrument itself — the population must be non-empty, and
the walk must still *find* the retired tables it is allowing, so the
main clause cannot pass by having stopped reading them.

### Mutations verified red and reverted (5)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `d1d5a30`.

| # | mutation | reddened |
|---|---|---|
| Q1 | `roles.md` serves `correlate/v1` again — the finding itself | 2 clauses: the walk (*"docs/design/roles.md:40  correlate/v1"*) and the pinned row |
| Q2 | a guide names a retired id in a fresh sentence | the walk — *"docs/guides/cli.md:3  correlate/v1"* |
| Q3 | a retired *row* drops its marker while its table keeps others | the walk — *"docs/design/architecture.md:882  correlate/v1"* |
| Q4 | `directions.md` drops the sentence that exempts it | `test_the_exemption_still_earns_itself` |
| Q5 | the README's paragraph loses its retirement sentence | the walk, twice — *"docs/README.md:82  analyze/v3"*, *"plane2/v1"* |

Q3 is the one that changed the code: it passed against the first
version of this guard, and the row/paragraph split exists because that
mutation survived rather than because it was designed in.

### Deviation from the Required Fix

- The filing asked for a guard over "`docs/design/`, `docs/guides/` or
  `docs/README.md`", which is what shipped — `docs/spec/` is out
  because it is ground truth and names every id by design, and
  `docs/audits/` and `docs/backlog/` are out for the reason review 5
  gave for review 4's own text: a dated record naming the version that
  existed then is correct.
- The filing's phrasing was "outside a sentence that says it is
  superseded". Implemented as three marker phrases rather than a
  general reading of the sentence, and the marker list is asserted to
  stay short by being written down rather than by a clause — a
  mechanical guard cannot tell a sentence that *says* a thing from one
  that mentions it.
