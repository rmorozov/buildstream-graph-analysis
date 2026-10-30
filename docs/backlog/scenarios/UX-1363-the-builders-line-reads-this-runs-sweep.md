# UX-1363: the builders recommendation reads this run's own sweep

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R5 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_builders_line_reads_this_runs_sweep.py`

## Motivation

`analyze` on the fdsdk capture recommends "Builders: 1 with --jobserver auto", citing `13-mixed-graph, 16 cores: 143.6s -> 118.3s`, another project on another host. This run's own `bga sweep` reads 21,330 s at 1 builder against 13,267 s at 4 (+61%).

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

The builders line cites this run's sweep or replay; a reading from elsewhere is labelled as such and never stands alone as the evidence.

## Out of Scope

Re-deciding the jobserver default (UX-1014).

## Acceptance Test

On the fdsdk capture the line does not recommend fewer builders than the sweep's knee without a reading from this run. Mutation: restore the fixture citation; the guard reds.

## Decision

The line's figure was `safe_builder_cap` alone — `max(1, host cores - the chain's max-jobs)`, 4 - 4 -> 1 on fdsdk — and its only evidence a `13-mixed-graph` reading from another project and host, hard-coded in `bga/cli.py`.

- `bga/cli.py`: `_own_sweep` replays this run at 1..`sweep_top` builders (the range `capacity_recommendation` sweeps) and reads the knee; `_builder_pool_text_lines` prints this run's replay first — builders at the recommended count against 1, and the knee — then the safe-cap rule, labelled "a rule read on another fixture … not on this run".
- `bga/correlate.py`: `with_own_sweep` sets `builders = max(safe cap, knee)`; with no sweep there is no builder count, only the ready-set width.
- The page: `builder_pool_recommendation` is text-only (not in `analyze/v9`), so the line renders nowhere on the page; the page's builders answer is `capacity_recommendation`'s card, which already reads this run's sweep (`Lower builders from 4 to 3: … the sweep's knee is at 3 builders`), and no `13-mixed-graph` text reaches it.

`test_builders_and_pool_are_recommended_from_a_capture.py` and `test_the_auto_advice_names_its_memory_bound.py` pinned the fixture-only line; each now hands it a sweep whose knee (4) is under the safe cap (8), so `Builders: 8` stands on a reading.

Guard: `tests/unit/test_the_builders_line_reads_this_runs_sweep.py` — fdsdk's sweep figures through the two functions, the no-sweep case, and `bga analyze` on a base-plus-four-leaves run whose knee (4) is above its safe cap (1).

## Outcome (2026-10-30)

**Gap measured** — `bga analyze /home/claude/fdsdk-cap/run`, before:

```text
Builders: 1 with --jobserver auto - the host's cores less the critical path's own max-jobs=4, so it can widen into the rest (13-mixed-graph, 16 cores: 143.6s -> 118.3s)
```

`bga sweep /home/claude/fdsdk-cap/run`:

```text
  Capacity      T_C (s)    Improvement
         1     21330.50           0.0%
         2     14641.10          31.4%
         3     13606.90           7.1%
         4     13267.10           2.5%
         5     13219.75           0.4%
```

**Close measured** — same command, after:

```text
Builders: 3 with --jobserver auto - this run's replay puts 3 at 3.8 h against 5.9 h at 1, its knee at 3; the --jobserver auto safe cap (host cores less the critical path's max-jobs=4) is 1, a rule read on another fixture (13-mixed-graph, 16 cores: 143.6s -> 118.3s), not on this run
```

Page (`bga view <snapshot>/run --reanalyse --export`, Plane 2 beside it, Chromium 1243, body text): `Lower builders from 4 to 3: the graph binds — the sweep's knee is at 3 builders`; no `13-mixed-graph`, no `jobserver auto`.

**Mutation table** — `python3 -m pytest -q tests/unit/test_the_builders_line_reads_this_runs_sweep.py`:

| mutation | reddened | count |
|---|---|---|
| `builders = safe_cap` (the fixture's figure stands) | knee-over-cap, no-sweep, analyze-on-a-run | 3 failed, 1 passed |
| restore the old line text (the fixture citation alone) | knee-over-cap, cap-above-knee, analyze-on-a-run | 3 failed, 1 passed |
| reverted | — | 4 passed |
