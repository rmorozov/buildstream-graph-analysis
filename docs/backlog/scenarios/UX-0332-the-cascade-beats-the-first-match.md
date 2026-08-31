# UX-332: the cascade beats the first match, and two record nits

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-318 (the guard it repairs) | **Serves:** the maintainers | **Topic:** guards

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

## Outcome (round 48, 2026-08-27) — 🟢 Done

### The evasion, reproduced

Appending one rule to `bga/viewer/style.css`:

```css
main .map-table { max-height: 20rem; overflow-y: auto; }
```

```text
before   21 passed          the nested scrollbox is back and nothing says so
after     3 failed, 19 passed
```

The three that redden are the static clause, the booted chain walk,
and the focus walk - the same three the *original*-rule route reddens,
which is the equality the acceptance asks for.

### Why the booted walk was no protection

This is the half worth naming. `UX-318`'s log argued the walk over the
booted page would catch a second route because it does not read the
stylesheet. It does read it: `_map_table_scrolls()` hands the walk a
flag derived from the sheet, **first-match**, so the browser rendered a
scrollbox while the walk was told there was none. Both halves of the
guard agreed with each other and disagreed with the page.

### The shape of the repair

`cascade(selector)` merges every rule for that selector in source
order, later winning - which is the whole tiebreak for textually
identical selectors, and the whole of what `UX-332` implements. A
cascade engine is out of scope and would be needed only to compare
*different* selectors.

Both scroll sites go through it, and a third clause drives the merge
on a stylesheet it builds - because the two clauses above pass either
way while the real sheet has only one `main .map-table` rule.

### Three record repairs

- **`UX-318`'s log** gains an inline correction with what round 45
  measured, rather than leaving a falsified sentence in a closed
  Outcome.
- **`UX-316`'s log** headed nine mutations "eight, all discriminating".
  Now nine.
- **The review log's commit column is dropped.** The filing says its
  hashes "are no objects in this repo"; measured, that is too strong
  and the real defect is worse-shaped: all four **are** objects in a
  clone that has fetched branch refs, and **three of the four are not
  reachable from `origin/main`**. So the identity resolved on the
  author's machine and not in an ordinary clone, and the one that does
  resolve (`b17d741`) does so by luck of which pull request kept its
  commits. "Closed rows at review" was already the merge-stable
  identity - a count in the tree, and what the cadence guard measures
  distance in.

Dropping the column shifted the findings cell from index 4 to 3, and
an existing clause read column 4 by number: it raised `IndexError`
rather than saying anything about findings. It reads the **last** cell
now - a guard that breaks on a column change is a guard that gets
deleted at the next one.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | the appended-rule route — round 45's evasion, verbatim | 3 |
| M2 | the original-rule route | 3, the same three |
| M3 | `_merge` goes back to first-match | 1: `a_later_rule_is_the_one_that_counts` |
| M4 | the commit column comes back | 1: `the_log_cites_no_hash_a_clone_cannot_resolve` |

**M3 is the one that changed the work.** On its first run it reddened
**nothing**: `cascade()` and the mechanism clause had *separate* merge
code, so mutating one left the other green, and the real sheet cannot
tell first-match from merge because it holds one such rule. They are
one implementation now - `cascade()` delegates to `_merge` - and the
mutation lands.

### Deviation from the Required Fix

- The Required Fix offers "dropped **or** replaced by something
  merge-stable" for the commit column. Dropped: the merge-stable
  replacement it names ("the closed-row count already is") was already
  in the table, so replacing would have meant adding a second column
  saying what the third already said.
