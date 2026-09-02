# UX-552: the CLI guide's alias table is two rows short

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** a reader looking up what `bga` can run | **Topic:** docs

## Motivation

Architecture review 12, checklist 4:

```text
docs/guides/cli.md:47-65   17 rows
bga --help                 19 aliases
absent from the table      timeline, view
```

Both have their own sections later in the same file, so the reader who
scrolls finds them and the reader who reads the table does not. Neither
is round 80's; the gap predates this review.

`docs/design/architecture.md`'s CLI table is guarded against `bga
--help` and is complete at 21 rows — this one is guarded by nothing,
which is the whole difference.

## Required Fix

Two rows, and the same derivation the architecture table has if it is
cheap: the table is `bga --help`'s alias block, so a guard can compare
them rather than a reader noticing.

## Out of Scope

- The per-command sections below the table: checked against `bga
  <name> --help` for both missing entries and both are current, so the
  gap is the table alone.

## Acceptance Test

The table's rows equal the alias block of `bga --help`, checked rather
than counted by hand.
