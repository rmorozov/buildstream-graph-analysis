# Walk, seed 7 - 0.6.3 release gate, 2026-11-27, commit 81f3512d

The 0.6.3 release walk (release guide condition 3). Base `81f3512d`, 2026-11-27; the
candidate is `5b6c37ec` (`UX-1385`, 2026-11-26). Driven on the reporters' model (89k tokens,
12 calls, 1.3 m); judged here: no blocking finding; 2 is filed with 3 folded into it, 5 filed,
1 is the cut itself (`UX-1391`), 4 needs per-process records the fixture lacks, 6 and 7 hold.

```text
seed 7 (bga/viewer, R6 CI user, Plane 2 spine on, cold capture, current contract, population many, reader = export). No `bst` or `bwrap` on the box ("[FAIL] bst-present", "[FAIL] bwrap-present"), so example 06 was not captured: `tests/fixtures/macro_micro/run` with its `plane2.json` beside it stood in. Spine on and population many were not reached: spine_policy off, 11 elements.
capture      fixture stamp 2026-08-21 · 11 elements · 813 processes (plane2.json, no per-process records) · planes: P1 + P2 report, trace none · cold only.
answer key   diff of example 06 against `optimized/`: 3 fixes. 2 match, 1 partial of 3.
  (1) core.bst `notparallel`: match - correlate "its native build asked for -j1: remove `notparallel`"; analyze "removing the pin is a single-line change".
  (2) chain -> fan-out: match - correlate restructuring `unread-gating-chain`, high, 8 elements, 43.2 s -> 19.05 s.
  (3) codegen only for lib-f: partial - `declared-not-used`, severity info, on lib-a..e and app, and on lib-f too.
per plane    P1 analyze | "chain-bound ... core.bst 19.1 s -> fixing it saves 12.1 s (26.1% of the build)" | match | yes | none
             P2 correlate | key (1)-(3), 18 recommendations, 47.8 KB of JSON | match/partial | yes | finding 4
             capacity | "Capacity checks ... did not run for this run - missing: the --max-jobs value" | match | yes | finding 5
page         headline right (chain_bound, core.bst) · macro findable (rail "What to fix first") · 678 controls, not driven (reader = bytes) · plane2 false, trace none · 58 sections · export 371,976 B, over_budget false
perfetto     0 canned queries (`has_timeline: false`); the export still carries `#perfetto` and 210 ui.perfetto.dev links. Nothing added.
findings     (raw; verdicts are the judge's)
 1. non-blocking (release) - `bga --version` -> "bga 0.6.2"; the cut bumps it (UX-1391).
 2. non-blocking → UX-1389 - `bga view run --export e.html` with `plane2.json` beside the run prints "Plane 2 was captured — its report is beside this run — but the raw trace log ... was not kept"; the page it wrote says "Plane 2 was not captured for this run, so there is no per-process detail" (census plane2 false, `grep -c cc1plus` 0). `bga view` has no `--plane2` flag.
 3. folded into UX-1389 - `bga analyze run` and `bga correlate run` find the `plane2.json` beside the run unasked (stderr "Plane 2: <path>"); `bga view` does not.
 4. non-blocking - correlate lists lib-f.bst `declared-not-used` on codegen.bst, which `optimized/` keeps; the fixture's plane2.json has no per-process records, and the row says "evidence, not a verdict". A real capture is needed to tell. No row.
 5. non-blocking → UX-1390 - `bga analyze run --format text` line 91, one Note: "--max-jobs is modelled for this capture from its own Plane 2 measurements" and "Capacity checks ... did not run ... missing: the --max-jobs value", while line 116 reads "max-jobs 4".
 6. holds - "This is the nightly scenario, so a 0% hit ratio is the intent" on a cold fixture with caches off: the run-context states no scenario, and caches-off is what the sentence keys on.
 7. environmental - the seed's capture recipe needs `bst` and `bwrap`.
rows added   0 - UX-1389 and UX-1390's answer-key rows ride their fixes
friction     the seed's spine-on and many-population classes need a real capture; finding the 3 answer-key hits in 47.8 KB of correlate JSON took a script.
```
