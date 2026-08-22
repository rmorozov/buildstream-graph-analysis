# UX-201: the schema says what things are, all the way down

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-193 (view-hints v1), UX-190 (the schemas), Direction 7 second iteration

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

---

## What was built

The external review's two live wrongnesses, reproduced against the
shipped renderer before anything moved:

```text
peak_rss_mb: 512   ->  "512 B"      (_mb guessed as bytes)
cpu_pct: 42        ->  "4200.0%"    (_pct guessed as a 0..1 share)
```

and after:

```text
peak_rss_mb: 512   ->  "512.0 MiB"
cpu_pct: 42        ->  "42.0%"
```

**1. Hints resolve recursively.** `hintsOf(node)`, `childNode(node,
key)` and `quantityFor(node, key)` are the three pieces; the renderer
threads the schema node alongside the value, so a nested property
carries its own semantics. `quantityFor` is the *one* place the
precedence lives — declared beats guessed — so that is a property of
the code rather than of every call site remembering. `guessQuantity`
survives as the explicit fallback and complains under
`BGA_STRICT_HINTS`, because an undeclared key is a schema gap.

Two quantities joined the closed set for exactly these cases:
`megabytes` and `percent` (0..100, not multiplied again).

**2. Columns are objects.** `bga:columns` v2 entries carry
`{key, title, quantity, sortable, description}`; plain names still
parse, because a column that needs nothing said about it should not
have to say it. `renderTable` stopped sampling row values to decide
numeric-ness, and the sorter stopped guessing — a column declared
unsortable stays unsortable whatever its values look like.

**3. The item shapes entered the schemas.** `findings[]` declares
id/severity/title/detail/elements with `severity` as an enum, so the
semantic renderer reads a contract instead of five hardcoded names.

**4. `verdict_kind` joins `compare/v1`**, emitted from the same branch
as the sentence — deriving it anywhere else would be a second
significance chain to keep in step. The banner styles from the enum and
falls back to prose only when the enum is absent; `verdictClass("THE
BUILD GOT WORSE, MATE", "regressed")` is `refused`, and the enum wins
over a contradicting sentence. Its default is `None`, not
`"not_comparable"`: a result built by something other than the
significance chain records nothing rather than claiming the strongest
refusal.

**5. Descriptions are the popovers**, sourced from the schema — and
thence the spec — rather than from prose written beside the renderer
where it would drift.

Tests: 20 new. Six mutations, each red, including the one that restores
the pre-fix state (dropping the recursive walk) and one that lets
`verdict_kind` default to a claim.

**A harness defect of mine, caught by its own test.** The popover probe
read `n.attrs.title` and reported an empty list against a working
popover: `el()` assigns non-`data-` attributes as *properties*
(`node.title = …`), which a browser reflects onto the attribute but a
shim does not. It checks both now.

**Deviation from the Required Fix:** item 3's "explicit named-view
registry keyed by schema name" is not built. The generic/semantic split
is still a shape test inside `renderSection`; the declared item shapes
are in, which is the half that removes the hardcoded field names, and a
registry with two entries would be indirection without a second reader.
Noted rather than silently skipped.

