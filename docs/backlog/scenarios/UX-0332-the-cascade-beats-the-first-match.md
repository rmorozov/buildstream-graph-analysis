# UX-332: the cascade beats the first match, and two record nits

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-318 (the guard it repairs) | **Serves:** the maintainers | **Topic:** guards

## Motivation

Round 45's verification proved the round-44 landing thirteen ways
and found one real evasion: the nested-scrollbox guards are
**first-match blind** — `test_the_fold_says_how_deep_it_goes.py:142-149`
and `_map_table_scrolls()` (`:525-532`) stop at the first
`main .map-table` rule, so a *second* rule appended later in
`style.css` — which wins the cascade in a real browser — restored
the scrollbox with every guard green (verified live), while the
same declarations in the original rule red three. UX-318's log
sentence "a second route to a nested scrollbox would redden too"
is falsified for this route. Two record nits ride along: UX-316's
log heads nine mutations "eight, all discriminating", and
`architecture-review.md:63`'s commit column cites hashes that are
no objects in this repo (squash-merge workflow — the column
cannot survive it).

## Required Fix

Both scroll clauses collect **all** rules per selector and judge
the cascade's winner (last wins), so the appended-rule route reds;
UX-318's log gains the correction note; UX-316's count fixed; the
review log's commit column dropped or replaced by something
merge-stable (the closed-row count already is).

## Out of Scope

- A general CSS-cascade engine — two selectors' rules collected
  is the need.

## Acceptance Test

The appended second `main .map-table` scroll rule reds both the
static clause and the booted walk (the round-45 evasion, inverted
into the guard); the original-rule route still reds; the review
log carries no unresolvable hashes (guard: every cited hash
resolves, or the column is gone).
