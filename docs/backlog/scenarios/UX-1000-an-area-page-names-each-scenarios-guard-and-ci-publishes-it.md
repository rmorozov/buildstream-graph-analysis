# UX-1000: an area page names each scenario's guard, and CI publishes it where it can be read

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-996, UX-997 | **Blocks:** — | **Found by:** round 139 — Ruslan in the project thread, 2026-09-23 17:34: "original idea was to use these docs for test plan coverage assessments as scenarios"; he chose both halves on the decision card at 17:35 | **Serves:** whoever assesses an area's test plan, and reads it on GitHub rather than from a checkout | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-996` stopped committing `docs/backlog/areas/*.md`; `dev_close_task.py
--areas` prints the same page (255 rows for `tools` today against the
committed 251 on main). Two gaps stay. The page can no longer be browsed
on GitHub, and it never was a coverage view: a row names a task and its
topic, not the guard that holds it, so an area's untested scenarios are
not visible on it.

## Required Fix

1. Each `--areas` row names the guard test file its task names (the
   Acceptance Test, else a `holds:` marker), and whether that file
   exists; a page closes with its covered/total count.
2. CI publishes the pages to the `records` branch through
   `dev_records.py publish` (`UX-997`), so they read on GitHub and
   never enter main.

## Out of Scope

Whether a named guard passes; which tests a scenario should have.

## Acceptance Test

To be named by the `architect`'s Decision.
