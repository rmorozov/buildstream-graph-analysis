# UX-585: the card's guard column is counted, not read

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-505 (the card) | **Serves:** the session that trusts the card's guard column | **Topic:** guards

## Motivation

`docs/contributing/rules.md` has 30 rule rows (not the 34 `UX-505`'s
Outcome says); 12 name a guard. Read against the tests:

```text
guard asserts the rule                 8
guard asserts adjacent tooling only    3   (test_the_loop_stays_fast: -n auto and the selector, not that a session ran it;
                                            test_the_order_the_page_has: one order guard; "three questions": text exists)
guard named does not hold the rule     1   (rules.md:56 spec outside Part 32 → test_docs_links_and_commands.py has no such clause)
unguarded                             18   of which enforcement EXISTS for two: :18 never-skip (the keep-the-guards hook),
                                            :29 annotate the moved figure (dev_close_task --figures)
```

`test_the_card_names_a_guard_for_the_rules_that_have_one` asserts
only that at least eight cells are populated — a wrong guard name
passes.

## Required Fix

- Each named guard carries a marker naming the rule it holds
  (a docstring line `holds: rules.md#<slug>`), and the card guard
  reads markers, not cell counts: every named guard must carry the
  marker for that row; every marker must appear on the card.
- The Part 32 rule gets its guard: a digest of the spec text outside
  Part 32's line range (`fixing-guide.md:105`), red on any change.
- The two rows with existing enforcement name it; the row count in
  `UX-505`'s Outcome annotated.
- The seven unguarded-but-mechanical rows (`:24`/`:52` pasted output,
  `:41` one id per commit, `:31` roles, `:45` unquoted `>=`) each
  get a one-line decision: guarded now, or judgment-shaped and said.

## Out of Scope

- Rewriting any rule — the card's sentences stay; only its guard column and the guards' markers change.

## Acceptance Test

Mutation: point a card row at a guard without its marker — red;
edit one spec line outside Part 32 — red.
