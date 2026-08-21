# UX-201: the schema says what things are, all the way down

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-193 (view-hints v1), UX-190 (the schemas), Direction 7 second iteration

## Motivation

The external review's P0, verified line by line in round 22: the
viewer's rule — *the schema determines what a field is* — holds only
at the top level. Hints are read from top-level properties
(`app.js:274-282`); every nested value falls to `guessQuantity(key)`
name-sniffing (`:61-68`), and the two systems demonstrably disagree:
`peak_rss_mb: 512` renders **"512 B"** (`_mb` maps to bytes),
a 0-100-scaled `cpu_pct` renders **"4200.0%"** (`_pct` maps to
share×100). Even hinted sections format their members by name
(`deltas`, `:185-188`). Adjacent confirmations, same class:
`renderFindings` hard-codes five field names while `analyze/v1`
declares `findings` as a bare array; `renderTable` decides
numeric-ness by sampling row values; `verdictClass` string-matches
the verdict *sentence* ("regress"/"improve"/"not comparable") because
`compare/v1` types `verdict` as a plain string.

One contract wave fixes the family:

## Required Fix

1. **Hints resolve recursively**: the renderer walks the schema node
   alongside the value (`render(value, schemaNode)`), so nested
   properties carry their own `bga:quantity`/`bga:direction`; the
   schemas gain the nested annotations the payloads already deserve
   (`deltas`' members, memory fields, shares). `guessQuantity`
   becomes the *explicit* fallback for undeclared keys and logs a
   dev-mode complaint — undeclared is a schema gap, not a feature.
2. **Columns become objects**: `bga:columns` v2 entries carry
   `{key, title, quantity, sortable}` — `renderTable` stops sampling
   and the sorter stops guessing.
3. **The item shapes enter the schemas**: `findings[]`
   (id/severity/title/detail/elements — severity as an enum) and
   `blast/v1`'s answer fields, so the two semantic renderers read
   declared shape; the generic/semantic split becomes an explicit
   named-view registry keyed by schema name.
4. **`verdict_kind` joins `compare/v1`**: an enum
   (`improved|regressed|no_significant_change|within_observed_range|
   not_comparable`) beside the sentence, emitted from the same
   significance chain the verdict-list guard already reads; the
   banner styles from the enum, never the prose.
5. **Descriptions render on demand**: every schema `description`
   becomes the field's popover — the "why is this number important"
   answer sourced from the schema (and thence the spec), not from
   viewer prose. Additive throughout; no version bumps (UX-190's
   rule).

## Out of Scope

- New analysis fields (UX-202's overview names its own needs).

## Acceptance Test

The two live wrongnesses become fixtures: a nested `peak_rss_mb`
renders as megabytes and a declared 0-100 share renders `42%`
(mutations: dropping the recursive walk reddens both). A column
declared non-sortable renders unsortable regardless of values. A
findings item missing `severity` fails schema validation (the
round-trip guard, extended). The verdict banner styles correctly
with the sentence wording scrambled and `verdict_kind` intact
(mutation: styling from prose reddens). Every popover text equals
its schema description byte-for-byte.
