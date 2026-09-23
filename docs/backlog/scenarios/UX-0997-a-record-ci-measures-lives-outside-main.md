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
