# UX-179: the discriminating case that was never built

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-173 (the guard this makes real), UX-176 (the standard it fails)

## Motivation

UX-173's acceptance named its one discriminating case precisely: *"a
synthetic graph where a stack-heavy blast outnumbers a cmake-heavy one
ranks below it by cost while the raw count says otherwise — asserted.
Mutation: treating stacks as building kinds reddens the discriminating
case."* The round-19 review proved it was never built, by the strongest
method available: **reverting the sorter to count-only order and
running the class — 3 passed.** On the golden fixture the cost order
and the count order are identical (the review printed both), the log's
claim that "the order is genuinely different from the count order
here, so this cannot pass by both orders agreeing" is false, and the
closing assertion (`len(set(weights)) > 1 or len(set(counts)) > 1`)
never compares the two orders at all.

The sorter itself is correct — this is a guard-claim finding, the
exact shape UX-176 was filed to hunt, shipped in the same commit range
as UX-176's own fixes. Two more guards from the same range that do not
guard:

- `bga blast` is outside `test_help_is_short.py`'s `SUBCOMMANDS`, so
  neither the 45-line cap nor the new terminator check runs over its
  help (24 lines today — true, unguarded).
- `_drop_size_memo`'s wiring is untested: the test calls the helper
  directly, and deleting the call in `bst_extract_run.py:503` reddens
  nothing.

## Required Fix

Build the acceptance's fixture: a graph where the count order and the
cost order **disagree** (stack-heavy blast outnumbering a cmake-heavy
one), assert the published `blast_radius_ranked_by` order differs from
the count order, and verify the original mutation now reddens. Add
`blast` to the help guard's list. Test the memo-drop through
`bga extract`, not the helper.

## Out of Scope

- The sorter and the split set (verified correct).

## Acceptance Test

The count-only revert reddens exactly one test, and that test's
fixture has provably different orders (both printed in the assertion
message on failure). `bga blast --help` violating the cap or the
terminator check reddens. Deleting the memo-drop call reddens the
extract-level test.

## What was built

The fixture the acceptance named: a graph where a stack-heavy blast
outnumbers a cmake-heavy one, so the count order and the cost order
**disagree**. The assertion compares the two orders directly (both
printed on failure) instead of asserting that some set has more than
one member, and the original mutation — treating stacks as building
kinds, or reverting the sorter to count-only — now reddens exactly
this test.

`blast` joined `test_help_is_short.py`'s `SUBCOMMANDS`, and
`test_every_subcommand_is_covered_by_this_file()` was added so the
list cannot silently fall behind the parser again: it reads the
registered subcommands out of the parser and fails on any that carry
no help guard. That guard is the general fix; adding `blast` was the
instance.

`_drop_size_memo` is now exercised through `bga extract` rather than
by calling the helper: deleting the call in `tools/bst_extract_run.py`
reddens the test, which it did not before.

Tests: 5 new (`tests/unit/test_blast_ranking_discriminates.py`) plus
the two guards above.

**Recorded, because the finding was about claims and not code:** this
item's own evidence method — revert the mechanism, run the class, see
what stays green — is the one that found it, and it is now applied to
every guard this round shipped.
