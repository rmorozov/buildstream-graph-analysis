# Walk, seed 6 - 0.6.1 release gate, 2026-11-03, commit ffcb221f

The 0.6.1 release walk (release guide condition 3). Base `ffcb221f`, 2026-11-03.
Driven on the reporters' model (97k tokens, 27 calls, 3.4 m); judged here: no blocking
finding; 3 and 5 filed, 1 is the cut itself (`UX-1378`), 2 is `UX-95`'s header on a fixture
with no identity, 4 needs a real capture to tell from the fixture, 6 and 7 hold.

```text
seed 6 (bga/structural, R3 graph owner, Plane 2 absent, incremental capture, current contract, population 0, reader = export bytes, no boot). No `bst` or `bwrap` on the box, so example 08 was not captured: `tests/fixtures/same_build_twice_incremental/run` stood in, `same_build_twice_cold/run` as the cold half. PYTHONPATH set to the worktree.
capture      fixture, no stamp (run_id "") · 4 elements (lib0-lib3, a chain) · 1 task traced, 0 processes · planes: P1 only, trace none. The fixture is not population 0: run-context reads processed 1, skipped 3, so the drawn class is not reached.
answer key   example 08 ships no `optimized/`; key from its README and the cold twin (8.0 s, 4 x 2.0 s chain): 2 match, 1 n/a of 3.
  (1) cold vs incremental: match - cold "100.0% of the 8.0 s critical path is 4 elements"; incremental "75.0% cache hit ratio (3 cached, 1 rebuilt)".
  (2) nothing to fix scheduler-side: match - "0.0% ... execution-bound", "Change the graph or the work itself, not the scheduler."
  (3) per-process cost: n/a - Plane 2 absent by design, and the page says "Plane 2 was not captured ... no per-process detail."
per plane    P1 analyze | "chain-bound ... lib3.bst 2.0 s -> fixing it saves 2.0 s (100.0% of the build)" | match | yes (`bga whatif --element lib3.bst` saves 2.000s) | none
             P1 cache | "75.0% cache hit ratio (3 cached, 1 rebuilt) ... The cache did most of the work" | match | yes | none
             P2 correlate | `bga correlate inc --format json` -> rc 2, stdout empty, stderr "Error: no Plane 2 report given, and none beside inc. Pass one, or point this at a snapshot" | match to cli.md | no | finding 3
             capacity | "The capacity checks did not run ... --max-jobs value, a core count ... missing" | match | yes | none
page         headline right (chain_bound, lib3.bst 2.0 s) · macro findable (rail "What to fix first", first section) · 345 controls in 30 classes, not driven (reader = bytes) · plane2 false, trace none · 46 sections, 4 tables · export 346,941 B, over_budget false · `#perfetto`, `#perfetto-link`, `#trace-download` sit in `hidden` spans
perfetto     0 canned queries (`has_timeline: false`); the absence line reads "queries below are what to ask it once there is one". Nothing added.
findings     (raw; verdicts are the judge's)
 1. non-blocking (release) - `bga --version` -> "bga 0.6.0"; the cut bumps it (UX-1378).
 2. non-blocking - `bga analyze inc --format text` -> "Run: " (empty), JSON `run_id` "" and `run_identity_available: false`; the fixture carries no identity. Nearest closed row UX-95.
 3. non-blocking → UX-1376 - `bga correlate inc --format json` -> rc 2, 0 bytes on stdout, a text error naming a report or `@last`, neither of which a Plane 2-less run has.
 4. non-blocking - `bga view inc --export export.html` prints "`bga timeline` renders one beside the snapshot."; `bga timeline inc` -> "no build.log here". The fixture keeps no build.log; a real wrap/extract capture is needed to tell. No row.
 5. non-blocking → UX-1377 - incremental run: "Bottlenecks Identified: 4 - lib0.bst, lib1.bst, lib2.bst, lib3.bst" where lib0-2 were cached; `bga whatif inc --element lib0.bst` -> "Refused: No measured duration: lib0.bst".
 6. non-blocking - UX-1342 (closed): cold "In this order: lib0.bst (6.0 s) -> lib1.bst (4.0 s) -> lib2.bst (2.0 s)" agrees with the top 3 and `whatif` (saves 6.000s); 4 equal elements cannot prove it either way.
 7. non-blocking - `bga release-notes --from 1280` -> "30 scenarios closed (closed-row markers 1280 → 1310)."; flags as cli.md says (UX-1341 holds).
rows added   0 - UX-1376 and UX-1377's answer-key rows ride their fixes
friction     population 0 is not reachable on this box: the committed incremental fixture rebuilds 1 of 4, so what a zero-rebuild second build shows needs a real `bst` run or a zero-population fixture.
```
