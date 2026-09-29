# UX-1073: compare reads each side's published analysis instead of analyzing both runs again

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5, R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement

**Guard:** test_compare_reads_published_analyses.py

## Motivation

`compare_runs` (`bga/compare.py:1320`) calls `analyze` on both runs
every time, though each snapshot published its `analyze.json` at
capture (`UX-296`). Two callers pay it on the hot path. 5,002 elements,
[the audit](../../audits/perf-snapshot-view-2026-09-28.md):

```text
snapshot tail  _compare         49.27s  peakRSS=2010MB  (2 analyze calls: 80.0 of 81.6s profiled)
bga view --export               54.93s  peakRSS=2038MB  (compare: 80.4 of 89.1s profiled)
```

At 1,202 elements: 3.44 s and 3.74 s. The view prints nothing until
it is done.

## Decomposition

Input classes: both sides published and current, one stale, neither published, a cross-mode pair (`UX-78`'s refusal). Journeys: the snapshot tail's compare and `bga view`.

## Required Fix

In `bga/compare.py` and `tools/bga_view.py`: `compare_runs` accepts a published analysis per side and uses it
only when its fingerprint equals the one this compare would analyze
under, falling back to analyzing otherwise. The fingerprint covers
every result-affecting input and option: the analyzer version, the
digest of each run-directory input, the digest of the Plane 2 report
actually passed (`--baseline-plane2`/`--candidate-plane2`), and the
normalized value of each option that changes the result (`--capacity`,
cold/history settings, and any other option the analyzer reads). Any
option not yet classified makes the analysis non-reusable rather than
reusable. `bga view --reanalyse` bypasses published analyses for the
comparison as well as for the page. The snapshot tail passes the
candidate's in-memory result with its fingerprint; `bga view` passes
both files. The analysis document's schema in `bga/schemas.py`
carries the fingerprint. The compare output is byte-identical either
way.

## Out of Scope

Making the analyzer itself faster (`UX-1074`).

## Acceptance Test

`tests/unit/test_compare_reads_published_analyses.py`: On the golden store: compare output from published analyses equals
the re-analyzed output byte for byte, and the number of `analyze`
calls is 0 with both published, 2 with neither. Each of these falls
back and analyzes: a bumped analyzer version, a changed `--capacity`, a
different Plane 2 report passed for one side, and `bga view
--reanalyse`. Mutation: ignore the published file, and the call count
reds; drop any one fingerprint term, and its case reds.

## Decision

Architect, adopted by the session:

- Route: new `bga/fingerprint.py`. `cli.analyzed()` stamps an optional
  `fingerprint` key on the analysis: producer stamp, sha256 of every
  run-dir input file, sha256 of the Plane 2 report, and result-affecting
  options. `compare_runs` (`bga/compare.py:1320`) reads each side's
  sibling `analyze.json` and skips `analyze()` only when fingerprints
  match. Options classified by walking the analyze parser's dests
  against two tables in fingerprint.py: RESULT (capacity, replay,
  heuristic, diagnostics, cold, allow_partial_cold, history_dir as a
  digest) and INERT (verbose, format, section, by_kind, explain,
  full-section flags); a dest in neither gives fingerprint=None (not
  reusable). `bga compare --reanalyse`; `bga view --reanalyse` passes it
  on in `payloads`. The snapshot tail needs no edit.
- The Plane 2 mismatch: compare analyzed Plane 1 only, while the
  published `analyze.json` comes from `analyzed()` with `--plane2`, so
  fingerprints would never match. Session default (Ruslan asked;
  reversible): compare analyzes each side through `analyzed()` with that
  side's own Plane 2 report (`--baseline-plane2`/`--candidate-plane2`),
  as a separable hunk (`_side_argv`).
- Files: `bga/fingerprint.py` (new), `bga/cli.py`, `bga/compare.py`,
  `bga/schemas.py` (`fingerprint` in `_ANALYZE_OPTIONAL` with hint;
  addition, no bump), `tools/bga_view.py` (payloads only),
  `tests/unit/test_compare_reads_published_analyses.py`.
- Guard: golden-store copies, published compare JSON equals
  `--reanalyse` byte for byte; `analyze` calls 0 with both published, 2
  with neither; falls back on a bumped version, a changed `--capacity`,
  a different Plane 2 report on one side, and `--reanalyse`.
- Mutations: compare ignores the file; drop each fingerprint term; move
  capacity to INERT.

## Outcome

**The gap, measured** on this track's base (`01d77fb6`), with the audit's
recipe (`gen-synthetic --store --seed 1`, `genlog.py ... 80 50`, the
report copied beside every snapshot), `step.py <store> compare`:

```text
1,202  compare   2.68s   peakRSS=140MB
5,002  compare  49.45s   peakRSS=2010MB
```

**The close, measured** after, both snapshots published by the tail's
own `_analyze`, then `_compare(prev, cur)` (and the fallback, `--reanalyse`):

```text
1,202  compare   0.32s   peakRSS=59MB     --reanalyse   3.87s  140MB
5,002  compare   1.27s   peakRSS=125MB    --reanalyse  60.44s  2006MB
```

The fallback is +11 s at 5,002: each side now runs `analyzed()` with its
Plane 2 report attached (the Decision's second bullet).

`tests/unit/test_compare_reads_published_analyses.py`:
`10 passed in 2.47s`.

**Which compare numbers moved** under the Plane 2 route, `jdiff` of
`bga compare -f json` at the base against this commit: the 1,202 store
(no admission rows in its report) and `same_build_twice_cold` vs
`_incremental`: **0 paths differ**. The guard's golden pair (candidate's
report carries a 1,000 µs `admission_wait` on `lib.bst`): **41 paths**,
all from `UX-1005` taking the wait out of BUILD - `deltas.lb` 0 ->
-1000, `element_deltas` `lib.bst` 0 -> -1000, `scheduler_wait_us`
+1000, the diagnosis sentence 100% -> 93%. Before, compare read Plane 1
alone and saw two identical runs.

**The sibling report** enters as its sha256 exactly when
`plane2.absence()` reads its content (not declined, raw log present) and
as its existence otherwise. Hashing it unconditionally reds
`test_the_view_parses_nothing` (2 failed: startup opened the monolith);
size+mtime let a same-size rewrite with a forged mtime keep the
fingerprint while `plane2_absence` changed (verifier).

**Mutation table** (`mutate.py`, one mutation at a time, restored from
a copy; revert: 10 passed):

| mutation | reddened | run |
|---|---|---|
| `_analyze_side` never reads the file | byte-for-byte (0 reads), plane2, run-dir input, beside, sibling rewrite, view | 6 failed, 4 passed |
| drop `producer` | bumped analyzer version | 1 failed, 9 passed |
| drop `inputs` | changed run-directory input | 1 failed, 9 passed |
| drop `beside` | changed file beside the run, sibling rewrite | 2 failed, 8 passed |
| drop `plane2` | different Plane 2 report on one side | 1 failed, 9 passed |
| drop `options` | changed `--capacity` | 1 failed, 9 passed |
| `capacity` moved to INERT | changed `--capacity` | 1 failed, 9 passed |
| sibling back to size+mtime | sibling rewritten at the same size and mtime | 1 failed, 9 passed |
| sibling as existence only | sibling rewritten at the same size and mtime | 1 failed, 9 passed |
| unclassified dest `continue`s | unclassified option never reusable | 1 failed, 9 passed |
| `payloads` drops `--reanalyse` | `bga view --reanalyse` reaches compare | 1 failed, 9 passed |
