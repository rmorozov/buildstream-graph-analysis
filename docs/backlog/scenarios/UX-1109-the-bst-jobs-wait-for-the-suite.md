# UX-1109: the bst jobs wait for the suite and use nothing it produced

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** anyone waiting on a PR to go green | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** runner:bst-examples

**Guard:** test_the_bst_jobs_start_beside_the_suite.py

## Motivation

`bst-tests` and `bst-examples` need `[changes, test, bst-smoke]`
(`ci.yml:1218`, `:1354`) and read no output of `test`. The PR critical path is
`changes` 9 s → `test (3.12)` 1,300 s → `bst-smoke` 29 s → `bst-examples`
2,064 s (medians, newest 100 runs; the ledger's spread still reads 620-964s), against a run wall of 3,350 s. Starting
the bst jobs beside `test` would put the path at ~2,100 s (estimate from
the medians, not a reading).

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     `bst-smoke`, `bst-tests` and `bst-examples` drop `test` from `needs`: smoke needs [changes], the other two [changes, bst-smoke]. None reads anything `test` produces (no download-artifact, no needs.test.outputs, no carry restore)
Rejected:  the row's "bst-smoke keeps its own place" - bst-smoke needs `test` (ci.yml:1164), so the bst jobs (spread 620-964s) would still wait and save 0 s; the deviation goes in the Outcome
Files:     .github/workflows/ci.yml; tests/unit/test_the_bst_jobs_start_beside_the_suite.py
Guard:     `test` is not in the transitive `needs` closure of bst-smoke, bst-tests or bst-examples (the `_ancestors` shape of test_the_records_writers_are_one_chain.py)
Mutation:  put `test` back into bst-smoke's needs only - a direct-needs guard stays green, this one reddens
Class:     optimization - the bst jobs start after ~40 s instead of ~1,340 s (estimate from medians; the job's recorded spread is 620-964s)
Split:     CI track, after 1108
```

## Required Fix

`bst-tests` and `bst-examples` need `[changes, bst-smoke]`; `bst-smoke`
keeps its own place. With `UX-1108` a red `test` still ends a superseded run;
a red `test` on a live run leaves the bst jobs running, which is the price.

## Out of Scope

Moving any step between jobs.

## Acceptance Test

`tests/unit/test_the_bst_jobs_start_beside_the_suite.py` reads both jobs'
`needs` and refuses `test` in either. Mutation: put `test` back in
`bst-examples`' needs; it reddens. The Outcome carries the first three PR
runs' walls against the 3,350 s median.

## Outcome

### The gap, measured

```text
$ python3 -c "_ancestors(n, jobs) for the three bst jobs"   (base 438740ac)
A-ci-base.yml {'bst-smoke': ['changes', 'test'], 'bst-tests': ['bst-smoke', 'changes', 'test'], 'bst-examples': ['bst-smoke', 'changes', 'test']}
```

### The close, measured

```text
$ same, on the branch
ci.yml {'bst-smoke': ['changes'], 'bst-tests': ['bst-smoke', 'changes'], 'bst-examples': ['bst-smoke', 'changes']}
```

```text
$ the 12 named ci.yml guards + UX-1108's + this file + newest-python + generated-project, -n 2
300 passed in 26.68s
```

None of the three jobs reads `needs.test` or downloads an artifact (parsed:
`'needs.test' in json.dumps(job)` and `download-artifact` both False). The
first three PR runs' walls against 3,350 s are not read yet: nothing is pushed
from a track.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| A | `test` back in `bst-smoke`'s needs only | 3 failed: `test_no_bst_job_waits_for_the_suite[*]` |
| B | `test` back in `bst-examples`' needs | 1 failed: `[bst-examples]` |
| C | `bst-tests` needs `[bst-smoke]` (loses direct `changes`) | 1 failed: `test_every_bst_job_still_skips_on_a_docs_only_diff[bst-tests]` |

C was green on a first draft that read `changes` off the transitive closure;
the `needs` context holds direct needs only, so the check reads `_needs`.
Restored from a copy: 7 passed.

**Deviation (Decision over Required Fix):** `bst-smoke` also drops `test`, as
the Decision routes; the Required Fix's "keeps its own place" would save 0 s.
