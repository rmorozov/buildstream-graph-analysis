# UX-1358: an element's serial stretches are measured, and "already compute-bound" is refused while they are large

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R2, R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_serial_stretch_is_measured_not_averaged.py`

## Motivation

`bga correlate` says `bootstrap/gcc.bst` (40.2 min, 18.2% of the path) is "already compute-bound at 2.57 cores busy - nothing to gain from its parallelism". The same native report's `redundant_operations` holds a serial `autoreconf2.69` loop: 105 runs, 691 s across three gcc elements, 436 s in `bootstrap/gcc.bst` alone, one process at a time. A mean of cores busy is a proxy for "can this go faster with the same work"; the wall time spent at one busy process is the reading.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

Plane 2 publishes, per element, the wall seconds at <=1 busy work process and the command signatures that own the most of it. Correlate refuses "compute-bound" when that share exceeds a stated line, and names the owning commands instead.

## Out of Scope

Splitting configure from build phases (UX-102 owns that).

## Acceptance Test

On the fdsdk capture, `bootstrap/gcc.bst` reports >=400 s serial, `autoreconf2.69` first, and no "nothing to gain" sentence. Mutation: compute the stretch from mean concurrency; the guard reds. The page's element card shows the serial seconds and the owning commands; on this capture's page `bootstrap/gcc.bst`'s card names `autoreconf2.69` and no "compute-bound" sentence, read by the walker.

## Decision

- `tools/bst_native_build_tracer.py`: `per_element_parallelism[]` gains `element_span_s` (every matched process of the element), `serial_wall_s` (time in that span at <=1 `WORK_BINARIES` process), `serial_share`, and `serial_owners` (top 3 normalised signatures of non-orchestration processes by wall time inside the stretches). Additive: no schema bump (json-contracts versioning rule).
- `bga/correlate.py`: `_SERIAL_SHARE_LINE = 0.15`; over it, `already-compute-bound` is replaced by `serial-stretch`, naming the seconds and owners. The join row carries `serial_stretch`.
- `bga/findings.py` + `bga/provenance.py`: analyze finding `serial-stretch`, so `--explain` prints `_SERIAL_SHARE_LINE`.
- Page: the element card prints the join's advice, so it shows the `serial-stretch` sentence and no compute-bound one. An evidence block for `serial_stretch` was tried and dropped: 6 lines put the page at 166,755 B against `PAGE_BUDGET_B` 166,750.
- Guard: a fixture element, 40 s of autoreconf then 60 s at six `cc1`. Mutation: the stretch from mean concurrency.

## Outcome (2026-10-30)

**Gap measured** (fdsdk capture, today's `corr.json`):

```text
bootstrap/gcc.bst  already-compute-bound: "... already compute-bound at 2.57 cores busy, so there is nothing to gain from its parallelism"
redundant_operations[0]: /bin/perl -w /bin/autoreconf2.69 -I ../config -fvi  105 runs, 691.0 s, worst bootstrap/gcc.bst 405.6 s
```

**Close measured** (fixture; `python3 -m pytest -q -p no:xdist tests/unit/test_a_serial_stretch_is_measured_not_averaged.py`):

```text
mean_work_concurrency 6.0, element_span_s 100.0, serial_wall_s 40.0, serial_share 0.4
serial_owners[0] = /bin/perl -w /bin/autoreconf2.69 -I ../config -fvi, 40.0 s; [1] m4 -P aclocal.m4
serial-stretch: "... — 40.0 s of its 1.7 min (40.0%) ran at most one work process, over the 15.0% line, most of it in `/bin/perl -w /bin/autoreconf2.69 -I ../config -fvi` (40.0 s), `m4 -P aclocal.m4` (10.0 s): a serial stretch no job count shortens"
4 passed in 0.69s
```

The fdsdk reading waits on a re-capture: its `native-report.json` predates the fields (`[k for k in per_element_parallelism[0] if 'serial' in k]` → `[]`) and its native trace was not published, so `bga correlate` on it still prints the compute-bound line for `bootstrap/gcc.bst`.

**Mutation table**

| mutation | reddened | count |
|---|---|---|
| `stretches = [(lo, hi)] if profile["mean"] <= 1 else []` (from mean concurrency) | all four clauses | 4 failed |
| `_serial_stretch_step`'s `if share <= _SERIAL_SHARE_LINE:` → `if True:` | correlate and page clauses | 2 failed, 2 passed |
