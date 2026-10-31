# UX-1368: the builders line sizes every approach for the host's regime and proposes one

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** Ruslan on the fdsdk recheck (2026-10-31): "we need to size all approaches and make bga propose optimal approach" | **Serves:** R5 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_builders_line_sizes_by_host_regime.py`

## Motivation

On the fdsdk cold recheck (run 41226762092, 4 cores, chain max-jobs 4) `bga analyze` printed "Lower builders from 4 to 3" and "Builders: 1 with --jobserver auto". The auto rule, cores less the chain's max-jobs, was read on 16 Graviton cores and bottoms out at 1 on a host the chain already fills.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk/953683fb-cold-b4j4-41226762092`, untar `capture.tar.gz`, `--plane2 native-report.json`); fat-host and serial-chain sweeps as figures; `topologies._four_wide` at 4 and 6 cores through `bga analyze`.

## Required Fix

The regime is the host's cores against the chain's max-jobs: small (cores ≤ chain), serial (chain at 1), fat (otherwise). Each regime sizes off, auto, BuildStream's defaults, the configured pair and admission, each with its replay wall and the reading it stands on, and proposes one. Small and serial propose `--jobserver off`, max-jobs at most the cores, and the capacity recommendation's builders (else the knee); fat keeps UX-1363's safe cap under auto.

## Out of Scope

A contention-aware reading of auto or admission on a small host; a run whose whole `max-jobs` is 1 reads as a serial chain, though the lever there is max-jobs itself; the x86 16-core cells (UX-1280); the page, which reads `capacity_recommendation` and not this line.

## Acceptance Test

On the fdsdk capture the builders line proposes the capacity recommendation's 3 with the jobserver off, and lists auto at 1 as sized but not proposed. Mutation: propose auto everywhere; the guard reds.

## Decision

- `bga/correlate.py`: `host_regime` and `size_by_regime`; the builders recommendation carries `host_cpu_count`.
- `bga/cli.py`: the regime is read only when every chain element's width is known; small and serial print `_builders_off_lines`, every regime `_approach_lines`.
- `test_the_builders_line_reads_this_runs_sweep.py`'s `bga analyze` case moved to 6 cores, a fat host, where its claim (the cap stands under auto) still holds; its 4-core run is this guard's.

## Outcome (2026-10-31)

**Gap measured** — `python -m bga.cli analyze <cap>/run --plane2 <cap>/x/native-report.json`, before:

```text
    Lower builders from 4 to 3: the graph binds — the sweep's knee is at 3 builders; the host's cores allow 4, the memory allows 24.
Builders: 1 with --jobserver auto - this run's replay puts 1 at 4.8 h; the --jobserver auto safe cap (host cores less the critical path's max-jobs=4) is 1, a rule read on another fixture (13-mixed-graph, 16 cores: 143.6s -> 118.3s), not on this run
```

**Close measured** — same command, after:

```text
Builders: 3 with --jobserver off, max-jobs 4 - a small host: 4 cores, no more than the critical path's max-jobs=4, so the chain alone fills them and --jobserver auto has no idle cores to lend; this run's replay puts 3 at 3.1 h against 4.8 h at 1, its knee at 3; more builders buy 2.4% on the replay, which does not model their contention
  Approaches sized for 4 cores (replay wall, durations held fixed):
    off: --builders 3 --max-jobs 4 - 3.1 h; proposed
    auto: --builders 1 --max-jobs 4 --jobserver auto - 4.8 h; a 4-vCPU (2-core SMT) auto pair read 235 s -> 233 s, -1%, inside noise (UX-1004); builders = 4 cores less the chain's 4
    defaults: --builders 4 --max-jobs 4 - 3.0 h; BuildStream's own (max-jobs = min(4 cores, 8)): 16 jobs on 4 cores, as this run was configured
    admission (BGA_ADMISSION=1): not proposed - slower than auto alone on 13-mixed-graph, 16 cores (202-217 s against 182 s)
```

**Mutation table** — `python -m pytest -q tests/unit/test_the_builders_line_sizes_by_host_regime.py` (copy, assert one landing, restore):

| mutation | reddened | count |
|---|---|---|
| M1 every host is fat | regime cases, fdsdk, small-host cases, analyze | 7 failed, 7 passed |
| M2 builders ignore the capacity recommendation | capacity-over-knee, fat, serial | 3 failed, 11 passed |
| M3 small max-jobs not clamped to cores | clamp | 1 failed, 13 passed |
| M4 approach rows never printed | fdsdk approaches, fat, analyze | 3 failed, 11 passed |
| M5 auto at the safe cap everywhere (the old line) | fdsdk, small-host cases, serial, analyze | 6 failed, 8 passed |
| reverted | — | 14 passed |

**Deviation**: the evidence is thin at both ends, two small-host readings (UX-09, UX-1004) and no fat x86 reading (UX-1280); every row says which reading it stands on.
