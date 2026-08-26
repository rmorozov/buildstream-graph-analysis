# UX-322: the CLI table has lost the viewer

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** R2 — whoever is looking for what this tool can do | **Topic:** docs

## Motivation

`docs/design/architecture.md`'s command table is the one place a
reader goes to ask "what commands are there". It has eighteen rows.
The tool has twenty:

```text
in the table but nowhere else:  (none)
working and not in the table:   bga view
                                bga timeline
```

Both were checked by running them:

```text
bga view      --help  -> works
bga timeline  --help  -> works
```

`bga view` is the entry point for the **entire viewer axis** — every
round from `UX-193` (round 21) to `UX-320` (round 44), something like
forty closed scenarios, the export, the rail, the drawings, the visual
contract. `bga timeline` is `UX-188`'s two-plane trace and `UX-298`'s
native Perfetto emitter. A reader consulting the table to find out
whether this tool can show them anything sees neither.

They are not *absent* from the document — the prose mentions `bga view`
at four places and `bga timeline` at two. They are absent from the
**table**, which is the surface built to be read as a list.

## Why this is filed and not fixed

Found by review 4. A review that fixes what it finds is a fix session
wearing a review's name.

## Notable: this is a recurrence

`UX-245` was "the architecture's CLI table is two commands behind",
found by review 1 and closed. Three reviews later the same table is
two commands behind again, and this time the two are the axis the
project has spent the last twenty-four rounds on. The pattern is worth
a thought in the fix: a table maintained by hand against a parser that
knows the answer will drift again, and
`test_the_documents_keep_up_with_the_contracts.py` already
demonstrates the shape of a guard that would not let it.

## Required Fix

Both commands get a row, with what they report and their
not-spec-mandated marker like the other eight. And — the part worth
more than the two rows — a guard that compares the table against the
CLI's own subcommand list, so the third recurrence is a red test
rather than a fourth review.

## Out of Scope

- Rewriting the table's other rows. They were checked against the
  parser by this review and all eighteen name a real command, so
  there is nothing to fix and touching them would widen the diff
  past what the finding supports.
- The module map (`UX-294`'s subject, a different list in the same
  document).

## Acceptance Test

Every command `bga --help` lists has a row in the table and every row
names a real command; the guard reddens when a command is added to the
parser without a row, and when a row names a command that does not
exist.
