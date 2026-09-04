# UX-600: the rules card has one guard it cannot mark

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-585 (the markers) | **Serves:** the session reading the card's guard column | **Topic:** guards

## Motivation

`UX-585` gave each guard named on `docs/contributing/rules.md` a
`holds: rules.md#<slug>` marker and made the card read markers rather
than count cells. One row could not be marked:

```text
rules.md:28   "Both status markers, same commit; the counts are derived"
              its guard is tests/unit/test_docs_links_and_commands.py,
              owned by another track in the same round
```

It sits in `UNMARKED` in `test_the_agent_configuration_holds.py` with
its reason, and `test_a_deferred_marker_is_still_missing` reds if the
marker lands and the entry stays — so the deferral cannot outlive
itself. It is one line of work, blocked only by the round's own
parallelism.

## Required Fix

The marker line into `test_docs_links_and_commands.py`, and the
`UNMARKED` entry removed in the same commit.

## Out of Scope

- The other rows — they carry their markers.

## Acceptance Test

`test_a_deferred_marker_is_still_missing` is what enforces the pair;
mutation: add the marker and leave the entry — red.

## Outcome

**Gap measured** (worktree at `8f51a26`, after `UX-599`'s commit). The
row, the guard with no marker, and the deferral holding it:

```text
$ sed -n 28p docs/contributing/rules.md
| Both status markers, same commit; the counts are derived | `test_docs_links_and_commands.py` |
$ grep -c 'holds: rules.md#' tests/unit/test_docs_links_and_commands.py
0
$ sed -n '970,974p' tests/unit/test_the_agent_configuration_holds.py
    UNMARKED = {
        "test_docs_links_and_commands.py":
            "another track owns the file this round; its row is "
            "`both status markers, same commit`",
    }
```

The row's guard is real: `test_the_status_marker_and_the_table_agree`,
`test_every_scenario_has_exactly_one_row_across_the_two_files` and
`test_the_index_counts_match_the_rows_they_index` are the two markers
and the derived counts. The marker was the only thing missing.

**Close measured.** One line into the module docstring, and `UNMARKED`
emptied in the same commit:

```text
$ pytest tests/unit/test_the_agent_configuration_holds.py \
         tests/unit/test_docs_links_and_commands.py -q
150 passed in 15.03s
```

| mutation | anchor | reddened | run printed |
|---|---|---|---|
| the Acceptance Test: marker in, `UNMARKED` entry left | `grep -c 'holds: …counts-are-derived'` → 1 | `test_a_deferred_marker_is_still_missing`: `test_docs_links_and_commands.py carries a marker now` | `1 failed, 9 passed in 0.14s` |
| marker slug truncated by one character | `grep -c 'counts-are-derive$'` → 1 | `…_carries_the_marker_for_its_row` (`no holds: … line`) **and** `…_names_a_row_that_names_it` (`the card has no rule with that slug`) | `2 failed, 8 passed in 0.16s` |
| `rules.md:28` rewritten `same commit` → `one commit` | `grep -c 'Both status markers, one commit'` → 1 | same two clauses — the marker names *that* sentence, not that row | `2 failed, 8 passed in 0.20s` |
| `UNMARKED = {"test_output_schemas.py": …}` re-added | `972: UNMARKED = {"test_output_schemas.py": "a fresh deferral"}` | `test_output_schemas.py carries a marker now` | `1 failed in 0.13s` |

**A guard that no longer discriminates.** With `UNMARKED` empty,
`test_a_deferred_marker_is_still_missing` iterates nothing and passes
vacuously. That is the intended end state — the debt is paid — but it
means the clause is now dormant rather than holding anything. The
fourth mutation is there to record that the mechanism still fires the
moment a deferral is added, so the clause is dormant and not broken. No
row filed: an empty debt list with a live mechanism is what `UX-585`
designed.

**Close:** `make test-touching` 12 files, 418 passed, 3 skipped in
35.83s. `make test-small` (the tier holding
`test_the_agent_configuration_holds.py`) 3841 passed, 36 skipped in
35.09s. `make lint` clean. `make test` not run — the orchestrator's.

**Deviation from the Required Fix:** none. `rules.md` was mutated and
reverted, never shipped; the diff is the two test files.
