# UX-1294: the CHANGELOG's task links resolve from the repository root

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** none | **Found by:** the docs audit (2026-10-02, finding 5): ~1,595 relative links in `CHANGELOG.md` do not resolve | **Serves:** R1, R8 | **Topic:** docs | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`tools/bga_release_notes.py` copies each row's link from `closed.md`,
where it is relative to `docs/backlog/scenarios/`. Pasted into
`CHANGELOG.md` at the root, every `](UX-NNNN-....md)` points at a file
that does not exist there, so a reader clicking a release's "What
landed" gets a 404 on every item.

## Required Fix

The generator writes links relative to the file the body lands in
(`docs/backlog/scenarios/UX-....md` for `CHANGELOG.md`). Shipped rows
get the same prefix only if UX-550's digest does not cover the body;
otherwise they stay and the guard's scope is stated in the Outcome.
A guard resolves every relative link in `CHANGELOG.md`.

## Out of Scope

Rewording any shipped row.

## Acceptance Test

The link resolver over `CHANGELOG.md` reports 0 unresolved (or only
the frozen rows, counted); a fresh `bga release-notes` body's links
all resolve from the root.

## Outcome

**Digest scope.** `state_digest` (`tests/unit/test_a_release_records_a_contract_state.py`) hashes `contracts` and `commands` only; no row body is covered, so shipped rows were rewritten. The body is covered by `test_every_generated_block_matches_the_generator`, which regenerates, so the generator changed first and the blocks were regenerated from it. Digest lines unchanged.

**Gap measured.** Resolver over `CHANGELOG.md` (relative `](target)` not a URL, `Path(target).exists()` from the root): 1595 unresolved.

**Close measured.** Same resolver: 0 unresolved. `render` in `tools/bga_release_notes.py` prefixes `docs/backlog/scenarios/` on every relative link (`_REL_LINK`), both per bullet. New `tests/unit/test_the_changelog_links_resolve.py`: 3 passed; with the generated-body and digest tests, 60 passed.

| mutation | reddened | count |
|---|---|---|
| `render` skips the `_REL_LINK` substitution | fresh-body test, generated-block test | 2 failed |
| one `docs/backlog/scenarios/` prefix removed from `CHANGELOG.md` | changelog-links test | 1 failed |
