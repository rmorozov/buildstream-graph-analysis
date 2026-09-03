# UX-610: the verdict record is not a published key

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-593 (which built it), UX-343 (one contract version) | **Serves:** R4, the CI gatekeeper asked to defend a red gate from the payload alone | **Topic:** contracts

## Motivation

`UX-593` built `bga.compare.verdict_provenance(comparison)` — the
evidence chain behind a regression verdict, with `document: compare/v2`
and every path resolving against the payload. It is not *in* the
payload:

```text
compare/v2 keys   28     carrying a verdict record   0
```

A new top-level key must be declared in `bga/schemas.py`, which was
another track's file in the round that built the record. The
alternative that was available — nesting it under `element_deltas` —
was refused, and rightly: it would put the verdict's record inside one
of the objects the verdict cites.

So the chain exists as a function and reaches no consumer that reads
the document.

## Required Fix

`verdict_provenance` is published as a `compare/v2` key, declared in
`bga/schemas.py` so the emitted-key and unit censuses see it, at the
top level where the verdict is.

## Out of Scope

- The chain's content and the CI comment's rendering of it — done in
  `UX-593`, and unchanged here.
- A version bump — declined: this is an additive key, and `UX-343`'s
  rule bumps on a rename, not an addition.

## Acceptance Test

The key in `bga analyze --schema` output for `compare/v2`, and a
mutation removing its declaration reddening the census.
