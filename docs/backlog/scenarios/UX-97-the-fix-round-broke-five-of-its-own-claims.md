# UX-97: the fix round broke five of its own claims in flight

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-84, UX-86, UX-88 (all done — this is their drift)

## Motivation

Round 11's commit-by-commit review found five regressions where a later
commit *in the same twenty-commit range* falsified an earlier commit's
shipped claim, and nothing backfilled. Each is small; together they are
the same disease UX-88 treated — docs asserting something checkably
false — reintroduced within a day, which is the argument for the two
enforcement items below being tests rather than edits.

1. **The published `findings[].id` list is stale, again.** UX-88
   shipped the full id table in `docs/guides/cli.md` ("15, all defined
   in `bga/findings.py`"); UX-92 then added `cache-hit-ratio` and
   `cache-transfer-cost` — `bga/findings.py` now declares 17, and the
   table misses both. UX-88's own acceptance ("every id emitted appears
   in the published list") was checked by a one-off script, so nothing
   catches the drift. **Fix: add the two ids, and make the list a
   test** (same shape as the two docs rules that already exist:
   enumerate ids in code, assert each appears in the table).
2. **UX-81's advertised discovery command no longer matches its own
   refs.** UX-86 inserted the capture mode into the ref name
   (`…/<ref>-<mode>-b4j4-<run_id>`), and the documented glob in
   `real-project-capture.yml` and UX-81's own doc still reads
   `<ref>-b4j4-*`, which matches nothing — while the listing pasted as
   UX-81's live evidence in the same file shows the `-incremental-`
   segment. Fix the glob in the workflow comment, the task file, and
   the status-table row.
3. **The bst-gated tier count says 14 in four places and 15 in the
   gate.** UX-91 added a fifteenth bst-gated test and moved CI's pinned
   count; `README.md`'s user-facing "fourteen tests… fails if any of
   the fourteen is skipped", UX-84's doc (three places, including a
   Verification Log quoting `14 passed`), UX-88's doc, and the status
   table were not moved with it. Fix the numbers — or better, stop
   hand-writing the count anywhere the pinned CI value can be quoted.
4. **The bst CI step can go green on a failing pytest.** The tier runs
   `pytest … | tee /tmp/bst-tier.txt` with no `pipefail`, so the
   step's status is `tee`'s. The count-check backstop catches ordinary
   failures (`14 passed, 1 failed` fails the `15 passed` grep) but not
   `15 passed, 1 error` (a teardown/collection error), which passes the
   grep and greens the job. Fix: `set -o pipefail` (or
   `defaults.run.shell: bash -euo pipefail`) on that step.
5. **Four stale bare paths survived the reorg** because the link test
   only sees markdown link syntax: `examples/05-…/project.conf` (two
   `docs/scenarios/…` references), `tests/unit/test_edg.py`
   (`docs/backlog/tasks/P1-18.md`, wrong filename), and — the one that
   matters — `tests/unit/test_docs_links_and_commands.py:108`, where
   the **assertion message printed to a failing contributor** points at
   `docs/style-guide.md`, which no longer exists. The test enforcing
   "links resolve" hands out a dead link when it fires.

## Required Fix

The five items above, plus the one guard that keeps 1 and 3 from
recurring: the findings-id table becomes test-enforced, and the tier
count appears in exactly one hand-written place (or none).

## Out of Scope

- New enforcement beyond the two named (bare-path linting repo-wide was
  considered by the reorg and is a larger, separate decision).
- UX-80's reopened acceptance (its own file tracks it).

## Acceptance Test

`grep -rn 'fourteen\|"14 ' README.md docs/backlog/scenarios/UX-84* docs/backlog/scenarios/UX-88*` shows no stale tier count; the id-list test fails when a finding id is added without a table row (verify by mutation); `git grep 'b4j4-\*'` shows only globs containing `-<mode>-`; the bst CI step fails on an injected pytest error (verify with a deliberately erroring test in a scratch branch or `act`-style dry run, or at minimum demonstrate `bash -c 'false | tee /tmp/x'` semantics before/after the pipefail change); the four bare paths resolve.
