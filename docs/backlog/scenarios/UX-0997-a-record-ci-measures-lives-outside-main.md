# UX-997: a record CI measures lives outside main, and main carries only reviewed commits

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-503, UX-524, UX-691, UX-934, UX-943 | **Blocks:** — | **Found by:** round 139 — Ruslan in the project thread, 2026-09-23 14:44, answering the workflow review ([doc](https://claude.ai/code/artifact/7f65768e-b4bb-405a-b3e1-90a672a249f5)) | **Serves:** every branch that inherits main, and every commit on main that should have CI | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

89 of the last 300 first-parent commits on main are CI adopt or append
commits, which get no CI of their own (`UX-934`), and 10 of 40 push runs
on main failed between 09-20 and 09-23. Six rows (`UX-890`, `UX-917`,
`UX-929`, `UX-934`, `UX-936`, `UX-943`) guarded the adopt jobs one
symptom at a time. The owner chose to stop committing them on
2026-09-23 14:44.

## Required Fix

`tests/ci_reference.json`, `tests/touch_map.json`,
`tests/flake_ledger.json` and the tier rows are written only by main's
CI, to a store outside main's history, and every run reads them at a
sha it prints. No job pushes to main.

## Out of Scope

What the records measure, and the gates that read them.

## Acceptance Test

`ci.yml` has no `git push` to the default branch, and a guard reddens
if one returns.

## Decision

The `architect`, round 139 (`UX-993`), at `0b9b72cd`.

```text
Route:     an orphan branch `records`, written only by main's CI, holds the same paths
           (tests/ci_reference.json, tests/touch_map.json, tests/flake_ledger.json and
           docs/audits/mutation.md, which mutation.yml also pushes to main). A new
           tools/dev_records.py: `fetch [--at SHA]` writes them at their paths (now
           git-ignored), prints `records @ <sha>`, writes tests/.records-sha; offline it
           reuses the last copy as "<sha> (cached)"; `publish` runs dev_adopt_check, commits
           on the records tip, pushes refs/heads/records. Readers keep their paths; make
           test/push-check/test-touching/test-tiers and CI's docs-lane, test and
           tier-reference fetch first. The branch is never force-pushed, so --at reproduces.
Rejected:  artifacts/caches - downloads and the caches API are denied through the proxy, and expire
           a release asset - no history, no diff, no git sha
           recompute on demand - multi-run medians and an append-only ledger (UX-496, UX-924, UX-691)
Files:     T1 (additive): ci.yml's three adopt jobs (publish, `concurrency: records`), mutation.yml's
           push, tools/dev_records.py, test_no_workflow_pushes_to_the_default_branch.py (new),
           test_a_run_names_the_records_it_read.py (new), the adopt-path guards that name the push.
           T2 (the move, after T1 merges and main has published once): `git rm --cached` of the
           four files, .gitignore, a Makefile `records` prerequisite, the fetch steps in ci.yml,
           the missing-record messages of the five dev_* readers, and the documents. RETIRE
           tools/_record_readers.py and test_a_record_selects_the_guard_that_loads_it.py (UX-942):
           no diff on main can hold a record any more.
Guard:     test_no_workflow_pushes_to_the_default_branch.py: every `git push` in every workflow
           names refs/heads/records or captures/*; test_a_run_names_the_records_it_read.py against
           a local bare remote: the tip sha printed, --at honoured, "(cached)" offline
Mutation:  restore `git push origin "HEAD:${{ github.ref }}"` in tier-reference-adopt; restore
           mutation.yml's bare push; drop fetch's sha print; ignore --at - each reddens. Retire
           check: a corrupt flake_ledger row before publish makes dev_adopt_check exit non-zero
Class:     process (directed by the owner 2026-09-23)
Split:     T1 now, parallel with #284 (no overlapping hunk). T2 serial after T1 has run once on
           main, after #284 (docs-lane) and after UX-996 (both edit dev_touching.py and
           test_the_process_documents_derive_their_figures.py)
Question:  none
```

### T1

**Gap measured:** `git show 49a29a29:.github/workflows/ci.yml | grep -c "git push"`
→ 3; `git show 49a29a29:.github/workflows/mutation.yml | grep -c "git push"` → 1.
4 literal `git push` lines across the two workflows, each landing a
bookkeeping commit on `main`.

**Close measured:** `grep -c "git push" .github/workflows/ci.yml
.github/workflows/mutation.yml` → 0, 0. The three ci.yml adopt jobs and
mutation.yml's ledger job now call `tools/dev_records.py publish`
instead. `python3 -m pytest -q -n 4 $(grep -l -e ci.yml -e mutation.yml
tests/unit/*.py)` → `812 passed`. `python3 -m pytest -q
tests/unit/test_a_run_names_the_records_it_read.py
tests/unit/test_no_workflow_pushes_to_the_default_branch.py
tests/unit/test_an_adopt_job_reads_its_record_before_it_pushes.py` →
`21 passed`. `make lint` clean (one new baseline entry, `tests/quality_baseline.json`,
authorised `UX-997`: `ruff S603` on `dev_records.py`'s own
`subprocess.run`). `python tools/dev_touching.py --base 49a29a29
--loud` green.

**Verifier fix (held T1 over one defect):** `fetch`'s failure was
swallowed by ci.yml's `|| true`, and `publish`'s own second fetch
(`_records_tip`) could then succeed - overlaying this run's delta onto
a tip the working tree was never actually read against, dropping any
row published since. `fetch` now records the tip it confirmed (`git
config --local bga.records-base`, `"none"` when the branch does not
yet exist); `publish` refuses - `::error::`, exit 1, nothing written or
pushed - unless that still matches the tip it sees now.
`test_a_run_names_the_records_it_read.py::TestPublishRefusesAStaleBase::test_a_swallowed_fetch_failure_refuses_rather_than_drops_a_row`
reproduces the verifier's exact repro (two checkouts of one bare
remote: one publishes a row, the victim's fetch fails, its own adopt
tool appends a different row, `publish` must refuse rather than lose
the first) → `9 passed` for the file, `21 passed` for the three files
above, `812 passed` unchanged for the ci.yml/mutation.yml population,
`make lint` clean.

### T1 Mutations

| mutation | reddened | count |
|---|---|---|
| restore `git push origin "HEAD:${{ github.ref }}"` in `tier-reference-adopt` | `test_no_workflow_pushes_to_the_default_branch.py` (2 of 3) | 2 failed, 1 passed |
| restore `mutation.yml`'s bare `git push -q` | `test_no_workflow_pushes_to_the_default_branch.py` (2 of 3) | 2 failed, 1 passed |
| drop `fetch`'s sha print | `test_a_run_names_the_records_it_read.py` (the 3 `TestFetch` cases whose stdout it asserted) | 3 failed, 5 passed |
| `fetch` ignores `--at` | `test_a_run_names_the_records_it_read.py::TestFetch::test_at_a_past_sha_is_honoured` | 1 failed, 7 passed |
| a corrupt `flake_ledger.json` row before `publish` | exercised directly (not mutated): `test_a_run_names_the_records_it_read.py::TestPublishRefusesARejectedRecord::test_a_ledger_its_guard_rejects_is_refused_and_nothing_is_pushed` asserts `dev_adopt_check` rejects it and nothing reaches the remote | passes green already; the guard *is* the falsification |
| drop the base-vs-tip comparison in `publish` (verifier's fix) | `TestPublishRefusesAStaleBase::test_a_swallowed_fetch_failure_refuses_rather_than_drops_a_row` | 1 failed, 8 passed |

Each mutation was reverted from the clean copy `falsify`'s step 1
saved and re-confirmed green (`812 passed`; `9 passed` for
`test_a_run_names_the_records_it_read.py`).
