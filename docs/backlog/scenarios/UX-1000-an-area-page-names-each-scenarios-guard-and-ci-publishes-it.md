# UX-1000: an area page names each scenario's guard, and CI publishes it where it can be read

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-996, UX-997 | **Blocks:** — | **Found by:** round 139 — Ruslan in the project thread, 2026-09-23 17:34: "original idea was to use these docs for test plan coverage assessments as scenarios"; he chose both halves on the decision card at 17:35 | **Serves:** whoever assesses an area's test plan, and reads it on GitHub rather than from a checkout | **Topic:** guards | **Area:** tools | **Shape:** mechanical

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

## Decision

The `architect`, round 140, at `8e2fd51f`.

```text
Route:     new tools/dev_area_pages.py takes area_page_body/report_areas from dev_close_task.py and
           adds a Guard column: every test_*.py the task's own text names, read from the
           Decision's Guard: line, then the Acceptance Test, then the Outcome, each marked
           present or missing under tests/; no file named reads "no guard named"; the page ends
           "covered N / M" (N rows naming >= 1 existing file, M rows listed). --areas still only
           prints; only `dev_area_pages.py --out DIR --link-base URL` writes. CI job
           area-pages-publish (push to default, needs [touch-map-adopt, flake-ledger-adopt],
           if !cancelled(), concurrency records, contents write): fetch, write to $RUNNER_TEMP,
           `dev_records.py publish --pages DIR` overlays docs/backlog/areas/ on the tip, pushes
           only on a change; links pinned to github.sha
Rejected:  holds: markers - resolve 0 of 567 (all 21 point at rules.md anchors)
           Acceptance Test alone - 116 (20%); Guard line alone 6 of 14; Outcome 234; all three 273 (48%)
           a reverse index of test docstrings - a proxy: agrees with the Acceptance Test's file in 34 of 116
           growing dev_close_task.py - a write path in a tool UX-996 keeps read-only
           a publish step inside an adopt job - those need a green test; pages need only text
Files:     T1: tools/dev_area_pages.py; tools/dev_close_task.py (page code moves out);
           tests/unit/test_an_area_page_names_each_guard.py; tests/unit/test_every_task_names_its_area.py
           (retire test_a_page_counts_the_rows_it_lists); tests/quality_reference.json
           T2: tools/dev_records.py (publish --pages); .github/workflows/ci.yml;
           tests/unit/test_ci_publishes_the_area_pages.py
Guard:     T1: three sandbox rows (existing file, test_absent.py, none) -> "covered 1 / 3"
           T2: temp repo + bare origin + records: publish --pages pushes pages beside untouched
           records, a second identical run pushes nothing; the job has concurrency records and
           fetches before publish
Mutation:  T1: drop the existence check -> "2 / 3"; M as len(ids)+1 -> red
           T2: publish's early "no record changed" return ahead of the overlay -> red;
           delete concurrency: records -> red
Class:     product - Ruslan's test-plan coverage view (2026-09-23 17:34, both halves chosen)
Split:     T1 parallel with UX-997 T2; T2 after both
Question:  none
```
