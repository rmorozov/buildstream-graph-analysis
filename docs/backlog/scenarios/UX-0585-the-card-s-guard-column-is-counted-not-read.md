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

## Outcome (round 83, 2026-09-03) — 🔴 handed back for the close

### The gap, re-classified on `5b4c05f`

The 30-row count holds. The rest of the classification does not:

```text
                                 Motivation   measured
rule rows                            30          30
rows naming a guard                  12          13    (11 distinct cells;
                                                        `make check-clean` twice)
unguarded rows                       18          17
guard asserts the rule                8           8
guard asserts adjacent tooling        3           3    :26 :32 :57
guard named holds no clause           1           1    :56
```

`UX-505`'s Outcome said **34** because its parse counted the four
`| rule | guard |` header rows as rules — that row is annotated in
place. The `:56` premise is confirmed exactly:

```bash
$ git grep -c "Part 32" -- tests/unit/test_docs_links_and_commands.py; echo "exit=$?"
exit=1
```

No output, exit 1: the named guard has no clause about Part 32 at all.

### The close, measured

```bash
$ python3 -m pytest tests/unit/test_the_spec_outside_part_32_is_read_only.py \
    tests/unit/test_the_agent_configuration_holds.py -q
110 passed in 2.17s
$ make test-touching
28 file(s) selected · 641 passed, 4 skipped in 29.93s
$ make test-small          # uptime: load average 5.67
3719 passed, 36 skipped, 1 warning in 17.24s
$ make lint
All checks passed!
```

### Mutations verified red and reverted (6, plus one green counterpart)

| mutation | reddened | run |
|---|---|---|
| row :34 pointed at `test_output_schemas.py` | `..._carries_the_marker_for_its_row` + `..._names_a_row_that_names_it` | 2 failed, 2 passed |
| the marker deleted from `test_output_schemas.py` | `..._carries_the_marker_for_its_row` | 1 failed, 3 passed |
| the Part 32 guard's marker re-pointed at `never-widen-scope` | both directions | 2 failed, 2 passed |
| a stray marker on a file no row names | `..._names_a_row_that_names_it` | 1 failed, 3 passed |
| an already-marked guard added to `UNMARKED` | `test_a_deferred_marker_is_still_missing` | 1 failed |
| **spec line 2940 edited, outside Part 32** | `test_the_digest_is_unchanged` | 1 failed, 3 passed |
| *counterpart:* spec line 1671 edited, **inside** Part 32 | nothing | 4 passed |
| `_outside()` aimed at Part 32 itself | `..._covers_most_of_the_document` | 1 failed |

### The guard that did not discriminate

`test_every_marker_in_the_tree_names_a_row_that_names_it` used `git
grep`, which reads **tracked** files only — so the new Part 32 guard,
still untracked, was invisible and mutation 3 reddened one clause where
it should have reddened two. Now `git ls-files --cached --others
--exclude-standard`, plus a clause asserting at least eight files carry
a marker so an empty scan cannot pass.

### Deviation from the Required Fix

- **Row `:28` is unmarked.** Its guard is
  `test_docs_links_and_commands.py`, another track's file this round.
  It is named in `UNMARKED` with the reason, and
  `test_a_deferred_marker_is_still_missing` reddens if it is marked and
  the entry stays. **Needs a follow-up row.**
- The seven mechanical rows: `:24`, `:31`, `:41`, `:45`, `:52` each say
  *judgement* and why, in the cell. `:18` and `:29` name the
  enforcement that already existed
  (`keep-the-guards-able-to-fail.sh`; `tools/dev_close_task.py
  --figures`, held by `test_the_loop_stays_fast.py`). That is seven,
  and `:24`/`:52` are the two the filing pairs.
- No rule sentence was changed — only the guard column, the markers and
  `UX-505`'s annotation.
