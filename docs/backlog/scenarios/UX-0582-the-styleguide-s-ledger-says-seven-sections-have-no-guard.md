# UX-582: the styleguide's ledger says seven sections have no guard

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-305 (the conformance checklist), UX-320 | **Serves:** the session that touches the page and reads §7 to find its guard | **Topic:** docs

## Motivation

Thirty-one guard files enforce the styleguide (539 passed, 8 skipped
without the example capture), and the guide's own §7 ledger
(`styleguide.md:1305-1333`) says "none with a guard yet" for seven
sections that have had one since rounds 59-70 (§1c/§1d, §2c-§2e,
§6b-§6d). Beside it: §3's "default 20" row cap has no constant to
point at (`grep -rn "\b20\b" structured.js tables.js schemas.py` →
a comment), §6b says 21 modules where there are 22, and §1's guard
checks module→guide in one direction only — the scalar rows (badge,
sentence, popover, banner, delta) have no `classify` row and no
reverse check.

## Required Fix

§7's prose ledgers replaced by one §→guard table, derived: a guard
reads `§[0-9][a-g]?` mentions across `tests/unit/*.py` and holds
the table to them both ways (a § with no guard is listed as such
with a reason; a guard citing a § that the table omits is red). The
"default 20" sentence names its constant or loses the number; §6b's
count derives.

## Out of Scope

- New rules — this is the index of the ones that exist.

## Acceptance Test

Mutation: delete a §-citing guard file — the table reds on that row;
add a § to the guide with no guard and no reason — red.
