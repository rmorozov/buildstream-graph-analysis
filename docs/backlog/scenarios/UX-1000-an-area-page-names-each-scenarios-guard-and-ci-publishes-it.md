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

## Outcome (round 140) — T1

### The gap, measured

Two columns, no guard, no covered count (`3a3b7d17`); the first cut
over-read the whole `## Outcome`, sweeping in the register footer and
the mutation table's own "reddened" column - covered 350/567.

### The close, measured

Two audits (seed 140, seed 141) found and fixed four false-negative
shapes, and reported nine further ones left unfixed by design. A third
audit (seed 142, 20 covered rows) found 2 false *positives*, both
Outcome-sourced: `UX-219` cites `test_a_report_you_can_navigate.py` as
the suite that caught an unrelated regression; `UX-826` cites two files
as limitations ("does not discriminate ... alone"). A near-miss,
`UX-397`, cites another row's guard as prior art. No regex tells "this
file proves my claim" from "this file is named while explaining why
it doesn't", so the page marks the *kind* of evidence instead of a
fifth extraction rule: **declared** (Decision `Guard:`, else Acceptance
Test) or
**inferred** (Outcome, legacy headings included); a row with both
counts declared, once. `python3 tools/dev_area_pages.py --areas` now
ends `covered N / M (declared D, inferred I)`:

```text
bga: 73/108              bga/replay: 1/1          tools: 171/256
bga/attribution: 2/3     bga/report: 3/3          tools/native_trace: 8/10
bga/diagnostics: 2/3     bga/structural: 2/4      unassigned: 53/75
bga/normalize: 1/1       bga/viewer: 48/102
tests/unit: 1/1                          TOTAL: 365/567 (declared 120, inferred 245)
```

Seed-141's remaining false-negative classes (a bare test function name,
never its file; an unrecognized heading; a filename split across
lines or sitting unbackticked in a fenced block - UX-530, UX-175,
UX-545 et al) are unchanged, still uncovered, still not chased.

### Mutations verified red and reverted (10)

| # | mutation | reddened |
|---|---|---|
| A1 | drop the existence check | `test_the_page_ends_covered_n_of_m` - "1/3" -> "2/3" |
| A2 | `M` as `len(ids)+1` | same clause - "1/3" -> "1/4" |
| A3 | `_outcome_guard_files` back to a whole-section scan | footer/mutation-table cases - "no guard named" -> shown, covered |
| A4 | row-count `len(listed)` -> `+1` | `test_the_page_names_the_row_count` - "3 row(s)" -> "4 row(s)" |
| B1 | `_MUTATIONS_SUBSECTION` back to `split(...)[0]` | `test_a_guard_cited_after_mutations_still_counts` - covered -> "no guard named" |
| B2 | `_BACKTICKED_GUARD_FILE` back to no-prefix pattern | `test_a_path_prefixed_citation_still_counts` - covered -> "no guard named" |
| B3 | `_outcome_sections` returns only `_section(text,"Outcome")` | `test_a_stub_then_real_outcome_reads_the_real_one` - covered -> "no guard named" |
| B4 | drop `_LEGACY_OUTCOME_HEADINGS` fallback | `test_a_legacy_verification_log_still_counts` - covered -> "no guard named" |
| C1 | swap the declared/inferred increment | 3 tests: "declared 1, inferred 0" -> "declared 0, inferred 1" and reverse |
| C2 | drop the ` (inferred)` suffix | 5 tests: `` `test_present.py` (inferred) `` -> `` `test_present.py` `` |

All ten reverted from a saved copy (`cp` before mutating, restored
after); green again each time.

### T2 (round 140) — CI publishes the area pages

Gap: `publish` wrote only the four record paths; nothing overlaid
`docs/backlog/areas/`, and `ci.yml` called `dev_area_pages` nowhere.

Close: `publish --pages DIR` diffs `DIR`'s `.md`s against
`docs/backlog/areas/` at the tip (name or content) and overlays them
beside whichever of the four paths changed; the "nothing changed"
return now waits on `tip`, so a pages-only run still publishes.
`area-pages-publish` needs `[touch-map-adopt, flake-ledger-adopt]`,
push-only, `concurrency: records`, writes pages to `$RUNNER_TEMP` with
links pinned to `github.sha`, then `publish --pages`. `pytest -q
tests/unit/test_ci_publishes_the_area_pages.py`: 5 passed - pages push
beside untouched records, a repeat publishes nothing, the job needs
both adopt jobs, shares `concurrency: records`, fetches first.

| # | mutation | reddened |
|---|---|---|
| D1 | return moved back ahead of `tip`/pages check | both `TestPublishPages` - error, no `refs/heads/records` |
| D2 | delete `concurrency: records` | `test_it_shares_the_records_concurrency_group` - `KeyError` |

Both reverted from a saved copy; green again.
