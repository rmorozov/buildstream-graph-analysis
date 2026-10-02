# UX-1254: the capacity operator assembles a sizing answer from five sections

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), brainstorm B2, filed at Ruslan's request | **Serves:** R5 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** test_an_agent_sizing_card_reads_its_sources.py

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §B2).

Sizing an agent (cores, memory, builders) reads `#occupancy` (builders 3.99x of 4), `#cpu_time` (40.4 min CPU = 0.86 cores of 4), `#peak_memory` (no process over 64.0 MiB), `#ready_queue` (peak depth 60) and `#capacity_recommendation` (keep 4, the graph allows 8). `roles.md` scores R5 Partial; no block puts those figures in one place or says what this build on this host wants.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     compute_agent_sizing(result) beside the recommendation publishes agent_sizing (builders recommended + graph ceiling; cores busy average + peak where host_cpu exists; memory per-element peak RSS x builders; caveat; one source section id per field); a new first section in the machine chapter draws it; Plane 1-only reads one absence sentence.
Rejected:  computing in viewer JS; a findings entry.
Files:     bga/correlate.py; bga/cli.py; bga/schemas.py; bga/viewer/chapters.js; bga/viewer/sections.js; tests/unit/test_an_agent_sizing_card_reads_its_sources.py.
Guard:     macro_micro agent_sizing values equal capacity_recommendation, plane2_capacity.cores_busy, memory_envelope, one link each; Plane 1-only gives the absence sentence.
Mutation:  memory from memory_envelope total instead of per-element peak.
Class:     product (page headroom ~9 KiB)
Split:     Track C, after B merges (reads host_cores name).
```

## Required Fix

One card in the machine chapter answers "what does this build want from this host": builders (recommended and graph ceiling), cores busy (average, and peak where Plane 2 has it), memory (per-element peak x builders), and the reading's caveat, each linking the section it comes from.

## Out of Scope

Cross-build aggregation (`store-aggregate/v1`); a queueing model.

## Acceptance Test

On this page the card shows builders, cores and memory with values equal to their source sections and one link each; a Plane 1-only run shows the card with cores and memory said absent in one sentence. Mutation: read memory from a different field, and the guard reds.

## Outcome (2026-10-01)

### The gap, measured

Base `62a86546`, `bga analyze --format json`: no key holds the answer.

```text
macro_micro --plane2:  agent_sizing None   (builders 4 -> 2 in capacity_recommendation,
                       cores_busy 1.60 there, 153.5 MiB largest peak only on element_join rows)
golden (Plane 1 only): agent_sizing None
```

### The close, measured

This branch, `#agent_sizing` drawn first in "Was the machine used well?":

```text
2,402-element page (seed 1, 40x60, binaries; 20260303T091500Z):
  Builders: 4 recommended; the graph allows 8; this run had 4 — Capacity recommendation
  Cores: 0.86 of 4 busy on average — Capacity recommendation
  Memory: at most 256.0 MiB, if all 4 builders peak together at 64.0 MiB (process peak) — Peak memory
macro_micro:
  Builders: 2 recommended; the graph allows 2; this run had 4 — Capacity recommendation
  Cores: 1.60 of 4 busy on average — Capacity recommendation
  Memory: at most 307.0 MiB, if all 2 builders peak together at 153.5 MiB (memory envelope) — Peak memory
golden (Plane 1 only):
  Builders: this run had 2
  Cores and memory need Plane 2, which this run did not capture.
```

Memory is an upper bound and says so; `memory.basis` names its input:
`envelope` (`memory_envelope`) or `process_peak` (Plane 2's per-element
peaks, when no host RAM was recorded - the 2,402 page).
`bga view --export`, before -> after: page half 159,921 -> 160,605 B
(`macro_micro`) and 159,923 -> 160,607 B (2,402 elements), +684 B against
`PAGE_BUDGET_B` 165,000; data half +2,244 B and +1,750 B. `macro_micro`'s
opened page: 872 controls (card +6 on 866).

Round 163's merged tree: `agent_sizing.caveat` dropped from the payload, the card reads
`capacity_recommendation.caveat`; macro_micro's data half 100,165 -> 99,891 B (99,981 under `-n 2`),
the guard's own measure against 100,000. M9: the key restored - equals-its-source: 1 failed.

### Mutations verified red and reverted (8)

| # | mutation | reddened |
|---|---|---|
| M1 | memory bytes from `memory_envelope.at_observed_builders` (the Decision's) | equals-its-source and both constructed cases: 3 failed |
| M2 | Plane 1-only absence reads "were not measured" | both absence clauses: 3 failed |
| M3 | `agent_sizing` second in the machine chapter | first-section, both pages x widths: 4 failed |
| M4 | the source link drawn as a `span` | one-link-a-row, both widths, constructed card: 3 failed |
| M5 | no fallback to Plane 2's peaks without host RAM | constructed no-RAM case: 2 failed |
| M6 | `basis` stays `envelope` on the fallback | constructed no-RAM case: 2 failed |
| M7 | the p95 cores row never drawn | constructed host-CPU card: 1 failed |
| M8 | "at most" dropped from the memory row | macro_micro page and constructed card: 3 failed |

