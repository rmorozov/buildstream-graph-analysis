# P3-10: Large multi-subproject synthetic-project integration test

**Priority:** P3 | **Status:** 🟢 Fixed & Verified (built and verified 2026-08-13) | **Depends on:** none

## What this is

A bigger, more realistically-shaped integration test than the single 3-node linear chain in `tests/test_e2e.py`: a synthetic BuildStream project with **four junctioned subprojects** (`core-utils`, `data-format`, `net-stack`, `ui-toolkit`), each providing one or more C++ shared libraries, linked into one root executable (`app.bst`) — 9 elements, 12 dependency edges, a diamond dependency (`libcore.bst` reached both directly and transitively by four other elements), and real `PROCESS`/`DOWNLOAD` resource contention across `TRACK`/`FETCH`/`BUILD` phases (24 scheduled task-phases).

Unlike every other fixture in this repo, the trace data is **not** hand-written JSON — it goes through the real pipeline a CI wrapper log would: a synthetic but format-correct BuildStream wrapper log → `tools/bst_log_to_chrome_trace.py` (a real, user-supplied, unmodified BuildStream-log-to-Chrome-Trace converter, now a first-class repo tool, not test-only glue) → an adapter into `trace/v9` → `bga.analyze_run`.

## Where it lives

- `tools/bst_log_to_chrome_trace.py` — the converter tool itself (reusable outside tests too).
- `tests/fixtures/synthetic_multi_subproject/build_model.py` — the element/dependency/duration model and a deterministic, capacity-aware list scheduler (ground truth; no randomness, fully reproducible).
- `tests/fixtures/synthetic_multi_subproject/adapter.py` — bridges the converter's Chrome-trace B/E events into bga's `trace/v9` span format (bga's own Chrome-trace ingestion only understands complete/`X` and phase/`P` events today — see the note below).
- `tests/fixtures/synthetic_multi_subproject/generate_fixture.py` — runs the full pipeline; `python3` this file directly to refresh the checked-in copies after changing the model.
- `tests/fixtures/synthetic_multi_subproject/project/` — a human-readable synthetic BuildStream project tree (`project.conf`, junctions, elements) matching the same model, for documentation only — not parsed by bga or by the test.
- `tests/test_synthetic_multi_subproject.py` — the pytest test file itself.

## A real format gap this surfaced

`bga.ingest.loader.load_trace`'s `'traceEvents'` branch only handles Chrome Trace `ph: 'X'` (complete) and `ph: 'P'` (phase) events. `tools/bst_log_to_chrome_trace.py` emits `ph: 'B'`/`'E'` (begin/end) pairs instead — bga's loader has **no handling for these at all**; they'd be silently ignored and the trace would come out empty. `adapter.py` bridges this gap for now. Promoting native B/E ingestion into `bga/ingest/loader.py` itself (so any Chrome-trace-producing tool, not just this fixture's adapter, works out of the box) is a reasonable follow-up but is its own scoped task — log it as a new tracker row if picked up, don't fold it into an unrelated task.

## Two new bugs found by this fixture (already filed separately)

Both were found by actually running the pipeline against this larger, more realistic shape, not by reading code:

- **P1-18**: `bga/structural/analyzer.py`'s `max_depth` uses `nx.shortest_path_length` (shortest hop count) instead of longest path, disagreeing with the correct `signals['unweighted_depth']` whenever a node has both a short and long path from a root — exactly this fixture's `app.bst`.
- **P2-05**: `bga analyze --format json` silently omits `structural`/`utilisation`/`confidence`/`violations` from output (a typo'd `hasattr(result, 'structural_metrics')` check plus several fields never referenced at all).
- Also **amplifies P1-03**: on this fixture's real multi-branch resource contention, the attribution-identity bug doesn't just undercount (as in the simpler reproduction) — it produces a negative `execution_on_chain_us` and a `dependency_wait_us` of ~453,000 years. See the updated `docs/backlog/tasks/P1-03-attribution-identity-resource-chains.md`.

Both new bugs, plus the amplified P1-03 evidence, are exercised as `@pytest.mark.xfail`-marked tests in `tests/test_synthetic_multi_subproject.py` pointing at their respective task files — remove the `xfail` mark as each is actually fixed, so the test starts guarding the invariant for real instead of just documenting the gap.

## Verification Log

```text
$ PYTHONPATH=. python3 -m pytest tests/test_synthetic_multi_subproject.py -v
...
8 passed, 3 xfailed in 0.89s

$ PYTHONPATH=. python3 -m pytest tests/ -v
...
22 passed, 3 xfailed in 1.81s
```

All non-`xfail` assertions pass, including: real-converter task-count reconciliation, the documented CACHED-with-no-START drop, checked-in-fixture-matches-model anti-drift check, graph shape (9 elements / 12 edges), `signals['unweighted_depth']` matching an independently-computed longest-path calculation exactly, critical path terminating at `app.bst`, I1/I2 floor invariants, and a full CLI subprocess run exiting 0.
