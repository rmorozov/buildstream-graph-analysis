# UX-205: tables you can interrogate

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-199 (between-sections navigation; this is within-section), UX-201 (the column metadata this uses), UX-187 (the scale that demands it) | **Topic:** viewer

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

## Outcome

All four items, and item 4's answer is **no virtualization** — with the
measurement that says so.

**The rule the whole thing rests on:** every comparison runs against
`data-raw`, the published value, never against the formatted cell text.
`> 5s` parses *because the column declares it is a `duration_us`* —
`UX-201`'s column metadata is what gives a suffix a meaning — and it is
compared with the raw microseconds. Comparing `"1.2s"` to `"5s"` as
strings is the defect the acceptance names, and mutating the comparison
to the rendered string reddens three guards.

1. **Per-table text filter**, matching any cell, with a badge that
   reads `12 of 1,202` while filtered and `1,202 rows` when not.
2. **Numeric thresholds** in the header of every quantity column, with
   the placeholder written in that column's own unit (`> 5s` for a
   duration, `> 512mb` for megabytes, `> 10%` for a share). Nine
   unit/quantity pairs are pinned by parametrised guards. **An
   unparseable threshold is no filter at all** rather than a filter
   that hides everything — a box nobody can read must not silently
   empty the table, and the input marks itself instead.
3. **Copy**: a row as JSON (published values, so it pastes into an
   issue as JSON that parses and equals the payload row), and a cell on
   double-click — its `data-raw`, not its rendering, because a copied
   `"1.2s"` pastes into nothing that computes. The clipboard write is
   best-effort: a page served over http on a non-localhost origin has
   no `navigator.clipboard`, and losing the copy is a nuisance where
   throwing would lose the report.
4. **The 4,000-row measurement**: render **146 ms**, filter **20 ms**,
   4,000 rows in the DOM, filter arithmetic agreeing exactly with the
   same predicate evaluated over the source array. Decision recorded:
   **windowed rendering is not built.** The caveat is stated plainly —
   this is a DOM shim under node, not a browser, so it establishes that
   the work is linear rather than that a real page is fluid. Machinery
   without a measured need is how a thin viewer stops being one; if a
   browser measurement later disagrees, the filter already operates on
   the full row set, which is the part windowing would have to keep.

**A real gap the tests found before a user could.** `applyFilters`
walked each row's *cells* looking for thresholds, so a threshold naming
a column that row does not carry was never checked and **every row
passed a filter that should have emptied the table**. It iterates the
thresholds now: "no value" does not pass `> 5s`.

**And the page ceiling, which this round genuinely crossed.** The
export was 82,775 B of page — over Direction 7's 80,000 B rule, and not
by an accounting quirk this time. The bytes were found where they
should be: **the inlined copy strips whole-line comments and blank
lines**, because this project's comments are written for someone
reading the repository and an attached report carries none of those
readers. Measured: 79,180 B of modules become 52,870 B; the real
`examples/06` export is now **62,152 B of page against 65,365 B of
data**, so the payload dwarfs the page again. The stripper is
deliberately not a minifier — only lines whose first non-space
characters open a comment, so a `//` inside a string or a regex can
never be touched, and code is left exactly as written.

Tests: 23 new. Six mutations, each red, including the acceptance's
named one. A seventh was written and **discarded as non-discriminating
rather than counted**: dropping the optional chaining from the
clipboard call still failed inside the `try`, so the guard stayed green
because the behaviour it asserts was still true. Removing the
`try`/`catch` is the mutation that tests the guard.

**Deviation from the Required Fix:** none. Cross-table queries and
column hiding stay out of scope as filed.
