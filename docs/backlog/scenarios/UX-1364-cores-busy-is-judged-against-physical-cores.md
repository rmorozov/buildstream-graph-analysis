# UX-1364: cores busy is judged against physical cores when the capture recorded them

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R5, R2 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** tests/unit/test_cores_busy_is_judged_against_physical_cores.py

## Motivation

The fdsdk runner is 4 logical CPUs on 2 physical cores (`capture-context.txt`, UX-1002), but `run-context.json` carries `cpu_count: 4` only, the pool is 4 "from host_cpu_count", and correlate's "compute-bound at 3.4 cores" thresholds read against 4. UX-1002 records the topology; nothing reads it.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

The run context carries physical cores; pool size and cores-busy judgements state both denominators when they differ.

## Out of Scope

Calibrating SMT yield (UX-1004).

## Acceptance Test

On a context with 4 logical / 2 physical, the pool line names both. Mutation: drop the field; the guard reds.

## Decision

`cpu_topology_counts` (tools/_run_context_common.py) is the one reader of sysfs; UX-1002's `cpu_topology()` string and the run context both come from it. `add_cpu_capacity_fields` writes `host_physical_cores` (affinity-restricted), `hostinfo.collect` writes `physical_cores` into the host manifest, `load_run_context` reads it. `hostinfo.core_denominators` renders `4 logical / 2 physical`, or `4` when equal, or `4 logical / physical unknown`. Printed in: the pool line (`unknown` said), correlate's "cores busy" judgements (single and grouped) and the capacity constraint "3.15 of 4 logical / 2 physical cores busy" (only when the two differ), and the page's Host row (`unknown` said), which reads `run_instance.host_manifest.cpu_label`, derived in the analyzer so the page carries no logic for it. Not touched: SMT yield calibration (UX-1004).

## Outcome (2026-10-30)

Gap measured, `bga analyze /home/claude/fdsdk-cap/run --plane2 /home/claude/fdsdk-cap/native-report.json | grep 'Pool size'`, before:

```text
Pool size: 4, from host_cpu_count (4) — no calibrated knee supplied via $BGA_CALIBRATED_CORES, so this is uncalibrated
```

Close, same command. Stored run-context (no field): `Pool size: 4, from host_cpu_count (4 logical / physical unknown) — ...`. With `host_physical_cores: 2` added to a copy of the run context:

```text
Pool size: 4, from host_cpu_count (4 logical / 2 physical) — no calibrated knee supplied via $BGA_CALIBRATED_CORES, so this is uncalibrated
    host_cores allows 4: 3.15 of 4 logical / 2 physical cores busy at builders=4, i.e. 0.79 cores per concurrent element
```

`bga correlate` on the copy: `grep -c "cores busy of"` 0 -> 3. Page, `bga view <copy> --reanalyse --export b.html`, dump-dom: `AMD EPYC 7763 64-Core Processor · 4 logical / 2 physical · 16 GiB` (before: `4 cpu`).

| mutation | red |
|---|---|
| writer drops `run_context["host_physical_cores"]` | 1 failed, 7 passed |
| `compute_builder_pool_recommendation` prints the bare count | 2 failed, 6 passed |
| correlate's `host_cores` forced empty | 1 failed, 7 passed |
| loader drops `host_physical_cores` | 2 failed, 6 passed |
| analyzer stops writing `cpu_label` | 2 failed, 6 passed (page, both cases) |
