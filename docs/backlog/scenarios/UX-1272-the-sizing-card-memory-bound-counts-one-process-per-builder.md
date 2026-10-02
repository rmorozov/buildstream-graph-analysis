# UX-1272: the sizing card calls builders x one process's peak "at most", while an element runs many processes at once

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), finding R3 | **Serves:** R5 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_an_agent_sizing_card_reads_its_sources.py` (the 2,402-element page's sizing inputs through `sizingCard` by node probe, process-peak row "not a bound"; `macro_micro`'s envelope basis in Chromium 1440x900 and 390x844)

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §R3).

`#agent_sizing` reads "Memory: at most 256.0 MiB, if all 4 builders peak together at 64.0 MiB (process peak)". 64.0 MiB is the largest single process (`#peak_memory` says it is deliberately not summed), but an element runs several at once: Plane 2 saw up to 33 alive together and every element asked for 4 jobs. So 256 MiB is a floor for four simultaneous peaks, not a ceiling, and "at most" is the wrong direction. An agent sized from it can OOM (cf. UX-1134).

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Route:     the memory direction follows the basis. For `process_peak`, the line reads "at least N: B builders x the largest single process (P); an element ran several processes at once", and the payload gains `memory.bound: lower`. For `envelope` (a whole element's peak), "at most" stays, with `bound: upper`.
Rejected:  processes-alive x process peak (33 x 64 MiB x 4 = 8.3 GiB, which treats every process as peaking together: a proxy that points the other way); per-element summed RSS (needs a concurrent RSS series Plane 2 does not record, which is the out-of-scope new sampling)
Files:     bga/correlate.py (compute_agent_sizing, comment at ~1336 and the `bound` key), bga/schemas.py (agent_sizing.memory description and bound), bga/viewer/sections.js (sizingCard memory row), tests/unit/test_an_agent_sizing_card_reads_its_sources.py
Guard:     tests/unit/test_an_agent_sizing_card_reads_its_sources.py: on the 2,402-element two-plane page (basis process_peak) the memory row does not contain "at most" and reads "at least" over builders x process peak; an envelope-basis fixture still reads "at most"
Mutation:  restore the unconditional "Memory: at most" in sizingCard: the page case reds
Class:     product
Split:     one track. It shares sizingCard and compute_agent_sizing with UX-1274, so put it in UX-1274's track or merge it before that track
Question:  Default taken; Ruslan may reverse: relabel as a lower bound instead of computing a concurrent quantity

## Required Fix

The memory line reads as what it is (a per-process peak per builder, a lower bound) or is computed from a measured concurrent quantity (per-element peak of summed RSS across live processes, or processes alive at once x process peak) with its direction stated.

## Out of Scope

New memory sampling (host series); the cores and builders lines.

## Acceptance Test

On this page the memory line does not say "at most" over builders x process peak; where a concurrent bound is published, its value is at least that product. Mutation: restore "at most", and the guard reds.

## Outcome

Gap measured (base `b35c30e31`; the Motivation's page rebuilt as in UX-1274's Outcome, `analyze --format json`'s
`agent_sizing.memory`, and the card drawn from it):

```text
                before                                                    after
page payload    {basis: process_peak, bytes: 268431360, builders: 4}     + bound: none
page card       "Memory: at most 256.0 MiB, if all 4 builders peak        "Memory: 4 builders × the largest single process (64.0 MiB) =
                together at 64.0 MiB (process peak)"                      256.0 MiB; not a bound: an element ran several processes at
                                                                          once and their summed memory was not recorded"
macro_micro     basis envelope, "at most ... (memory envelope)"           + bound: upper; the row unchanged
```

Close measured: `test_an_agent_sizing_card_reads_its_sources.py` 9 passed in 3.5s. No concurrent bound is published,
so the Acceptance Test's second clause has no value to check.

| Mutation | Reddened | Count |
|---|---|---|
| the process-peak row reads "Memory: at least ..." | `test_the_peak_row_says_it_is_no_bound` (the page case) | 1 failed, 8 passed |
| `sizingCard` memory row unconditionally "at most" (`m.bound === "upper"` -> `true`) | the same | 1 failed, 8 passed |
| every basis takes the process-peak row (`-> false`) | `test_the_card_leads_the_machine_chapter_with_one_link_a_row` [1440, 390] (envelope) | 2 failed, 7 passed |

Deviation: the Decision's "at least" (`bound: lower`) is not a floor either - a builder on a lighter element need not
reach the largest process's peak - so the process-peak basis states its product and says it bounds nothing (`bound: none`).
