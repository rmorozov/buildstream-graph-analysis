# UX-702: a performance ratchet at the gate

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-531 (the superlinear analyzer), UX-418 (the reference method) | **Serves:** R8 reading whether a round made `bga analyze` slower on the largest capture, which nothing today records | **Topic:** guards | **Area:** unassigned | **Shape:** bounded

## Motivation

`UX-531` measured `bga analyze` superlinear in elements; the page pays
for it. No guard reads the analyzer's wall time or memory, so the
number can move a round at a time unnoticed — the `UX-418` lesson, that
a slow file is small until CI times out, applies to the tool itself.
Every timing rule in this repository holds: nothing across machines,
consecutive runs must agree, the reference is CI's own.

## Required Fix

One CI step on the 3.11 runner: `bga analyze` and `bga view --export`
on the largest fixture, wall and peak RSS (`/usr/bin/time -v`),
recorded into `tests/ci_reference.json` beside the tier rows under the
same adoption path; a run reports when two consecutive runs exceed the
reference by an absolute margin (seconds and MB, not a ratio — `UX-420`)
and the diff touches the analyzer. Never in `make test`.

## Out of Scope

- A local benchmark — no reading taken here compares with CI's.
- Profiling or the fix for the superlinearity — `UX-531`'s.

## Acceptance Test

The reference carries `analyze_wall_s` and `analyze_rss_mb` for the
fixture; mutation: an `O(n²)` loop over elements added to
`bga/analyzer.py` on a branch — the step reports on the second run
and names the diff's file.

## Outcome (implementer track, 2026-09-06)

### The gap, measured

Nothing read `bga analyze`'s wall clock before this: `git grep
analyze_wall_s -- tests tools .github` found nothing on the base
commit. `tests/pages.xl_run` (`--layers 20 --width 200 --seed 1`) is
the largest fixture in the tree — 4,002 elements, 2.5 MB on disk
(`du -sh`) — already used by `UX-531`'s own bound and named there as
the size that item's own wall-clock guard could not carry (its
Outcome: *"a 23s guard needs a tier row this track may not write"*).

### The close, measured

`tools/dev_perf_ratchet.py` (new): `bga analyze` and `bga view
--export` (cold, no published `analyze.json`) each timed by
`/usr/bin/time -v`; the worse of the two on each axis is judged
against `tests/ci_reference.json`'s `analyze_wall_s`/`analyze_rss_mb`
by an absolute margin only (`ANALYZE_WALL_MARGIN_S=5.0`,
`ANALYZE_RSS_MARGIN_MB=50.0` — stated starting values, not
measurements, the same state `UX-420`'s `CI_DRIFT_FACTOR` started in),
confirmed over two consecutive runs via a `perf_carry.json` cache
(`UX-442`'s shape), reported only when the branch's diff touches
`bga/analyzer.py` (`tools/dev_touching.changed_files`). `--annotate`
reuses `dev_tier_drift.annotation` (given a `title` param) for
`UX-621`'s route. `dev_tier_drift.adopt` now folds `PERF_KEYS`
(`analyze_wall_s`, `analyze_rss_mb`) into the candidate add-only,
independently of the per-file shift — the "adoption path" the
Required Fix names. Reproduced the Acceptance Test's own mutation by
hand: touching `bga/analyzer.py` and running two consecutive
`--against` calls reports `"bga/analyzer.py changed and analyze+export:
… - two consecutive runs over margin"`; one run, or a diff that does
not touch the file, reports nothing (pasted in the track's own report).

```text
$ make test-touching
49 file(s) selected (13 census + 36 naming the change) · 1328 passed,
3 skipped in 283.84s (0:04:43)
$ make lint
All checks passed! / clean: 301 finding(s) match tests/quality_baseline.json
```

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| M1 | `exceeded`: absolute margin replaced by a ratio (`>= 1.1x`) | `TestTheMarginIsAbsoluteNotARatio` — 3 failed, 18 passed |
| M2 | `confirmed`: the two-consecutive-run AND dropped | 2 of 4 `TestTwoConsecutiveRunsAreRequired` clauses |
| M3 | `touches_analyzer`: hard-coded `True` | `test_the_diff_names_something_else` |
| M4 | `parse_time_v`: returns `(0.0, 0.0)` instead of raising | `test_parse_time_v_refuses_a_foreign_report` |
| M5 | `dev_tier_drift.adopt`: `PERF_KEYS` no longer add-only | `test_adopt_never_rewrites_an_entry_it_already_has` |
| M6 | `ci.yml`: `--annotate` dropped from the `--against` step | `test_the_workflow_asks_the_ratchet_for_an_annotation` |
| M7 | `ci.yml`: the `if:` gate dropped from the measurement step | `test_the_ci_steps_are_gated_to_the_3_11_runner` |

**One guard did not discriminate at first.** M7's original form checked
only lines containing `dev_perf_ratchet.py`, textually windowed — it
missed the measurement step, which never names the tool. Rewritten to
read every step's own `if:` field structurally; M7 above is the
rewritten version, verified red and reverted.

### Deviation

`tests/ci_reference.json` carries neither key yet — Out of Scope
forbids a local reading, so the reference is bootstrapped exactly as
`UX-420`'s was (`"files": {}` there; absent keys here), and
`_against`'s unrecorded-axis branch says so rather than failing. The
Required Fix says "the diff touches the analyzer"; I read this as
`bga/analyzer.py` specifically (the Acceptance Test's own mutation
target), not the wider set of modules `UX-531` also profiled
(`blame_chain.py`, `timestamps.py`) — a judgement call, reported rather
than guessed. `bga analyze` and `bga view --export` are measured
separately and the *worse* axis of each kept, rather than one
combined `/usr/bin/time -v` span — also a judgement call, since the
Required Fix names two commands but the Acceptance Test only two
scalar fields. `docs/contributing/fixing-guide.md`'s derived test-count
figure moved (495→496) from the new test file and was refreshed
(`dev_touching.py --spread --write`); `tests/quality_baseline.json`
gained two entries (`--force --reason UX-702`) matching the identical
`subprocess.run(["git", …])` pattern already baselined for
`dev_tier_drift.explained_by`.
