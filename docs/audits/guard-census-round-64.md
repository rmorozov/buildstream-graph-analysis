# The guard census — round 64 (`UX-403`)

The falsify ritual — mutate the mechanism, watch the guard go red,
restore — has run as a *sample* since round 18: each round mutates the
handful of guards it touches. Hollow guards were found that way in
rounds 18, 19, 23, 27 and 45, a hit rate high enough that the unsampled
majority certainly contains more. **A guard that cannot fail is worse
than no guard**: it spends suite time buying false confidence.

This is the sweep. It is not exhaustive and does not claim to be: the
unit of work is the *family*, one representative mutation each, so that
a family with no discriminating guard is found rather than a file.

## The scoreboard

Eleven families, one mechanism-revert mutation each, applied to the
committed tree and reverted after the run.

| # | family | representative guard | mutation | verdict |
|---|---|---|---|---|
| 1 | contract inventory | `test_every_emitted_contract_is_answerable.py` | `contracts.ids()` renamed out from under the derived inventory | **RED** (3 failed, 13 passed) |
| 2 | docs links + commands | `test_docs_links_and_commands.py` | a guide's relative link points at a file that does not exist | **RED** (1 failed, 35 passed) |
| 3 | plane2 destinations | `test_every_plane2_block_has_a_destination.py` | `process_count`'s declared destination renamed off the block | **RED** (4 failed, 8 passed) |
| 4 | element join merge | `test_the_merge_carries_every_field.py` | `DRAWN_ELSEWHERE`'s written reason for `element_join` removed | **RED** (6 failed, 4 passed) |
| 5 | chapters / ordering | `test_the_report_has_chapters.py` | `findings` removed from its chapter | **RED** (3 failed, 9 passed) |
| 6 | tier partition | `test_the_tiers_are_a_partition.py` | a 50-second file demoted to no tier | **GREEN** (14 passed) |
| 7 | review cadence | `test_the_review_has_a_cadence.py` | the newest review row deleted | **RED** (1 failed, 7 passed) |
| 8 | viewer seams | `test_the_viewer_splits_along_its_seams.py` | a module re-exports another, which the inliner cannot see | **RED** (1 failed, 46 passed) |
| 9 | unit census | `test_every_number_says_what_it_is.py` | `bga:quantity` removed from a store-aggregate distribution member | **RED** (1 failed, 46 passed) |
| 10 | declared quantity vs value | `test_a_declared_quantity_matches_its_value.py` | a share declared where the value is microseconds | **RED** (2 failed, 8 passed) |
| 11 | golden snapshot | `test_golden.py` | `analyze_run` renamed out from under the snapshot | **RED** (2 failed) |

**Ten of eleven discriminate. One did not.**

## Row 6, and what was done about it in this round

`test_the_tiers_are_a_partition.py` has fourteen clauses and all
fourteen stayed green while a fifty-second file left the `LARGE` list.
Every one of them reads the two lists against each other or against the
filesystem — *listed files exist*, *no file is in two tiers*, *every
file is in at most one* — and `small` is the default tier, so a file
that belongs in a tier and is absent from both is "small on purpose".
The module's own docstring names this escape in the *stale* direction
and never covers the missing one.

**Fixed here**, for the half that is legible without measuring
anything: a file that boots a real Chrome cannot be small and says so
in its own imports. Four were doing it from the small tier when this
ran —

```text
tests/unit/test_a_shapeable_population_is_drawn.py    2.2s
tests/unit/test_a_task_uid_is_not_a_label.py          1.7s
tests/unit/test_one_bucket_one_row.py                 1.9s
tests/unit/test_the_synthesis_reaches_the_page.py     2.6s
```

— all four above `MEDIUM_FLOOR_S`, three of them added in this very
round. They are listed now, and
`TestNothingSlowByConstructionIsSmall` keeps them there. Both of its
clauses were falsified: unlisting one file reddens the first, and
breaking the detection pattern reddens the second.

**Filed as `UX-418`** for the half that needs a measurement: an
unlisted file that is slow for any other reason is still caught only by
CI's small-tier timeout, which fails naming a budget rather than the
file. `--durations=0` already prints what is needed; nothing reads it.

## What this census does not cover

Stated so the next round knows what it inherits rather than trusting a
scoreboard wider than its evidence:

- **One representative per family.** A family whose representative
  discriminates can still hold a hollow file. 364 test files, eleven
  mutations.
- **Mutation shape.** Each mutation reverts a *mechanism* — a
  declaration, an entry, a name the guard reads. Guards that assert an
  arithmetic result would need a different shape, and the filing's Out
  of Scope excludes operator-level mutation testing deliberately.
- **The four browser-boot files** were re-tiered, not re-measured on
  CI's clock; the figures above are this container's.
- **The families themselves** were chosen by reading the suite, not
  derived. A family nobody named is a family nobody censused.

## The ratchet

`UX-403` asks the census to leave one. It already exists as a habit —
the `verify` skill requires every closing task file to record the
mutation that reddened its new guard — and this round's own five
closures each carry one. What the census adds is the retroactive half:
a family that has never been falsified is now visible as a row that is
missing from the table above.
