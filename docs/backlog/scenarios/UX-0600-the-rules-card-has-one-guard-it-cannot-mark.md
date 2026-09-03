# UX-600: the rules card has one guard it cannot mark

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-585 (the markers) | **Serves:** the session reading the card's guard column | **Topic:** guards

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
