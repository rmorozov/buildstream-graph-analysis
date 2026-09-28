# UX-1061: a pseudonym is keyed, stable, and keeps the name's shape

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 4 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

The owner must resolve what an outside reader says back to real
elements without hand work, and pseudonyms must name the same element
across captures so comparison classes survive sharing.

## Required Fix

A new `bga/anonymize.py`: `pseudonym = prefix + base32(HMAC-SHA256(key,
class ‖ value))[:k]`, `k` grown on collision; junction separators,
`.bst`, depth, extensions, character class and length band kept; the
result a valid element name. One key per project under `.bga/anon/`,
the map beside it at mode 0600; a key fingerprint for the manifest.

## Out of Scope

Walking a capture (UX-1062); resolving text (UX-1064).

## Acceptance Test

`tests/unit/test_a_pseudonym_is_keyed_stable_and_shaped.py`: same key
and value give the same pseudonym across two runs; a forced collision
grows `k`; the map round-trips; the key and map files are 0600.
Mutation: drop the class from the HMAC input, and an element and a
directory of the same name collide.

## Outcome

**Gap measured.** No `bga/anonymize.py` existed; nothing mapped a value
to a stable, class-salted, shape-preserving pseudonym.

**Close measured.** New `bga/anonymize.py`: `load_or_create_key`,
`key_fingerprint`, `PseudonymMap` (`resolve`/`has`/`add`/`save`/
`for_project`), `pseudonymize(value, cls, key, pmap)` (atomic token,
character class + length band kept, token length starts at the band's
own width and grows past it on collision) and
`pseudonymize_element_path(value, key, pmap)` (junction `:`, `.bst`,
directory depth kept, per-segment class). `tests/unit/
test_a_pseudonym_is_keyed_stable_and_shaped.py`, 8 cases:
`python -m pytest tests/unit/test_a_pseudonym_is_keyed_stable_and_shaped.py -q`
→ `8 passed in 0.29s`. `python tools/dev_sizes.py --check` →
`sizes ok: 152 file(s) measured, none above the cell`.
`python tools/dev_close_task.py --check` → `0 problem(s) over 8
propert(y/ies), 1027 backlog row(s)`. `make test-touching` reds
`test_every_module_is_on_the_map` (`bga/anonymize.py` is not yet in
`fixing-guide.md` §6's context map) - left unadded here, since
UX-1062 is the one that walks a capture with this module and names it
there; everything else in the selection passes
(`1752 passed, 3 skipped`, plus the one named failure).

**Mutation table.**

| Mutation | What reddened | Count |
|---|---|---|
| `_digest`: drop `cls` from the HMAC message (`msg = value.encode(...)` only) | `test_the_class_salts_the_hmac_so_an_element_and_a_directory_differ`, `test_digest_input_includes_the_class` | 2 of 8 tests failed; 6 passed |
| `pseudonymize`: `k = band` back to `k = min(band, 4)` (the verifier's finding - every token capped at 4 chars regardless of band) | `test_the_token_keeps_the_original_length_band` | 1 of 8 tests failed; 7 passed |

Both reverted from the pre-mutation copy; all 8 pass again
(`8 passed in 0.29s`).

**Deviation.**
