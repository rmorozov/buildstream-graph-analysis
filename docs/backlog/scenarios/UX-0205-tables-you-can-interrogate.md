# UX-205: tables you can interrogate

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-199 (between-sections navigation; this is within-section), UX-201 (the column metadata this uses), UX-187 (the scale that demands it)

## Motivation

Confirmed in round 22: tables sort (numeric-aware) and nothing else —
no text filter, no threshold, no way to reduce 1,202 rows to the
twelve that matter. UX-187 capped what the *text* report prints; the
page renders every row of every array unconditionally, which is the
right default for a viewer and unusable without tools on it. The
external review's list, trimmed to what the published data supports:

## Required Fix

1. **Per-table text filter** (one input, matches any cell,
   row-count badge shows `12 of 1,202`).
2. **Numeric threshold on any quantity column** (`> 5s` typed into
   the column header's filter — the UX-201 column metadata says
   which columns are quantities and in what unit, so `5s` parses).
3. **Copy affordances**: copy a cell, copy a row as JSON — the
   paste-and-go tradition, pointed at issues and chat.
4. **Virtualization only if measured slow**: render the 1,202-row
   and a synthetic 4,000-row table first; if interaction stays
   fluid, record the numbers and skip it (machinery without a
   measured need is how a thin viewer stops being one). If it is
   slow, windowed rendering with the filter operating on the full
   data.

## Out of Scope

- Cross-table queries (Perfetto's SQL owns hard questions —
  UX-204).
- Column hiding/reordering (wait for a request).

## Acceptance Test

The harness: filtering by text reduces the rendered rows and the
badge agrees; a threshold on a duration column parses `5s` against
`duration_us` values (mutation: comparing raw strings reddens);
copied row JSON round-trips through `JSON.parse` and equals the
payload row; the 4,000-row measurement is recorded in the log with
the keep-or-virtualize decision stated.
