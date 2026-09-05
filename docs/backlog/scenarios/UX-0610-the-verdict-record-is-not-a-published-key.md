# UX-610: the verdict record is not a published key

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-593 (which built it), UX-343 (one contract version) | **Serves:** R4, the CI gatekeeper asked to defend a red gate from the payload alone | **Topic:** contracts | **Area:** bga

## Motivation

`UX-593` built `bga.compare.verdict_provenance(comparison)` — the
evidence chain behind a regression verdict, with `document: compare/v2`
and every path resolving against the payload. It is not *in* the
payload:

```text
compare/v2 keys   29     carrying a verdict record   0
```

**Corrected in place, round 85.** The filed count was 28; re-measured
on `5343bd6` the emitted payload carries 29 keys — `UX-593` counted
without `schema`, which is a key. The 0 held exactly.

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

## Outcome

### The gap, re-measured on `5343bd6`

```text
$ bga compare a b --format json | keys                29   (filed as 28)
  of those matching provenance|verdict_record          0
$ verdict_provenance(comparison)
  document compare/v2 · evidence 4 paths · unresolved 0
$ schema(compare/v2): required 14 · properties 18
```

Both premises held; only the count was off, and it is corrected above.
The chain existed as a function whose every path resolved against a
document it was not in.

### The close

```text
$ bga compare a b --format json | keys                30
  verdict_provenance present, kind "verdict", document compare/v2
  == payload["schema"]
$ schema(compare/v2): required 15 · verdict_provenance in required
$ every evidence[].path re-resolved against the emitted payload
  unresolved 0 · resolved-flag disagreements 0
$ not_comparable -> key present, value null, document still validates
```

Required-and-nullable, not optional: `_document` types a required key
as `[kind, "null"]`, so a refusal validates and a consumer reads one
shape. Declared with `_PROVENANCE` — the same shape `analyze/v5`
publishes a claim's chain in — under its own description, because these
paths walk `compare/v2`.

**Superseded 2026-09-04 by `UX-629`** — `required 15` is now 14, and
*required-and-nullable* is now *permitted-and-always-written*. Below.

### Mutations verified red and reverted (7)

| mutation | reddened |
|---|---|
| the key declared optional rather than required | `…schema_declares_the_key` (+1) |
| `to_dict` never writes the key | `…in_the_payload_at_the_top_level` (+9) |
| nested under `element_deltas` instead | `…not_nested_inside_an_object…` (+4) |
| resolved against a document that is not the payload | `…every_evidence_path_resolves…` (+1) |
| a refusal publishes a record anyway | `…null_rather_than_dropping_the_key` |
| the declared shape dropped from the hint | `…the_one_every_chain_uses` (+1) |
| every quoted value replaced by `0` | `…what_the_payload_holds` |

`tests/unit/test_the_verdict_record_is_a_published_key.py`: 13 tests,
0.75 s single-process.

**One clause did not discriminate as first written.**
`…every_evidence_path_resolves_in_this_document` re-resolved each path
against the payload and passed under mutation 4, because a record built
against a *different* document spells the same keys — its own
`resolved: false` was the only trace. It now asserts the record's flag
agrees with the payload, and reddens.

### Deviation from the Required Fix

**Two surfaces beyond the two declared.** `_PROVENANCE.rule`'s
description was 24 characters ("What decided this claim."), under the
31 the popover guard requires. It had never been walked, because that
guard reaches `properties[key].properties[nested]` and every previous
use of the shape sat one level deeper. Lengthened once, in the shared
shape, so `analyze/v5`'s popover gains the same sentence.

And `UNDECLARABLE_ELSEWHERE` in `test_every_number_says_what_it_is.py`
gained the new key's `rule.threshold` — `UNDECLARABLE`'s own case, which
`candidate_diagnosis.provenance` already holds the twin of. Found by
that census, not by `make test-touching`, which does not select it.

**No version bump**, as the file declines: `UX-343` bumps on a rename.

**The renderers are unchanged.** `ci_comment.py` and `text.py` still
call `verdict_provenance(comparison)` rather than reading the new key —
`UX-593`'s rendering, out of scope here.

## Superseded by UX-629 (2026-09-04)

Both figures above stay; this is what moved them (fixing guide §3.6).

`schema(compare/v2)['required']` was **15** with `verdict_provenance`
in it and is **14** without. Entering `required` under a live id
stopped every `compare/v2` document written before this item from
validating against the id its author pinned:

```text
a 14-key compare/v2 document written before UX-610, against compare/v2:
  FAILS: 'verdict_provenance' is a required property
```

The key is *permitted-and-always-written* now — declared, listed in the
schema's own `bga:always_written` so `--schema` states the choice, and
guaranteed against the real payload by
`tests/unit/test_a_required_set_grew_under_an_unchanged_id.py` rather
than by `required`. The guarantee this item argued for is unchanged;
only its holder moved, and `compare/v2` did not have to become
`compare/v3`.

The first mutation in the table above — *the key declared optional
rather than required* — no longer reddens, because that is now the
correct state. Its replacement is the key leaving `bga:always_written`,
which reddens `…schema_declares_the_key` exactly as before.
