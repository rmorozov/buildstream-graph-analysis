# UX-1362: one element's saving is the same number in every section

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R1, R8 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_one_saving_per_element.py`

## Motivation

On the fdsdk capture, `analyze` Key Findings says fixing `bootstrap/gcc.bst` saves 30.6 min; Structural Analysis says "up to 1.0 s off the finish (0.0%)" for it and the four next. `correlate --format json` gives `potential_saving` 0.0 for doxygen and components/gettext while `whatif` says 509.55 s and 34.10 s.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

Every per-element saving printed by analyze, correlate and the page comes from the one `whatif` computation, or says which different question it answers.

## Out of Scope

Changing the whatif model.

## Acceptance Test

On the fdsdk capture the three readings agree for the 23 chain elements. Mutation: restore the structural ceiling's own figure; the guard reds. The page's element cards print the same savings, read by the walker on this capture.

## Decision

Three sources, one computation. Key Findings already read `realizable_saving_us` (`compute_realizable_savings`, whatif's function) but only for the 8 heaviest chain elements (`REALIZABLE_SAVING_CANDIDATES = 8`) and over summed task durations; correlate read the same field, so the other 15 published `potential_saving_us: 0`. Structural Analysis read `compute_sensitivity`'s `min(duration, next_binding_gap)`, where the gap is the graph's smallest positive slack: **1.0 s, held by `components/diffutils.bst`/`findutils.bst`/`gawk.bst`** off the chain, not the 50 ms epsilon.

- `bga/graph/edg.py`: the cap is 64 (fdsdk's chain is 23).
- `bga/analyzer.py`: `_build_critical_path_detail` evaluates every measured chain element over `compute_element_durations` (whatif's map); `_compute_structural_analysis` ranks `top_opportunities` by those savings (`_rank_by_realizable_saving`). Batching keeps slack's zero-slack list as its fallback, since two equal chains are worth 0 apart and something together.
- `bga/report/text.py`: the structural percentage names its denominator, "of the critical path" (Key Findings' is the build).
- The page reads `critical_path_detail`, `headline.top_actions` and `element_join`, so its cards follow with no viewer change.

Guard: `tests/unit/test_one_saving_per_element.py` — a 12-element chain with a 1 s near-tie beside `c1.bst`; detail, `sensitivity.top_opportunities`, correlate and `whatif.project` agree per element, and the text prints one figure. `test_realizable_saving.py`'s bound test now builds a chain past the constant.

## Outcome (2026-10-30)

**Gap measured** — `PYTHONPATH=. python3 three.py corr-before.json` (scratch: analyze, `whatif.project` per element, structural rows, `bga correlate --format json`) on `/home/claude/fdsdk-cap/run`, before:

```text
components/gettext.bst          detail=  -      whatif=  34.10 struct=  -    corr=  0.00
bootstrap/glibc.bst             detail=  -      whatif= 447.50 struct=  -    corr=  0.00
components/doxygen.bst          detail=  -      whatif= 509.55 struct=  -    corr=  0.00
bootstrap/gcc.bst               detail=1837.40  whatif=1837.40 struct= 1.00 corr=1837.40
components/_private/gcc-base.bst detail=2106.30 whatif=2106.30 struct= 1.00 corr=2106.30
```

`bga analyze`: `- bootstrap/gcc.bst: up to 1.0 s off the finish (0.0%)` (and four more), beside `fixing it saves 30.6 min`. Smallest positive slacks: `[(1000000.0, 'components/diffutils.bst'), (1000000.0, 'components/findutils.bst'), (1000000.0, 'components/gawk.bst')]`. Page (`bga view --reanalyse --export`, Chromium 1243, `#element-components-doxygen-bst`): `Share of path 3.9% · Duration 8.5 min · Element kind cmake` — no saving row.

**Close measured** — same commands, after: whatif equals correlate for all 20 measured chain elements, e.g.

```text
components/gettext.bst whatif 34.10 corr 34.10
bootstrap/glibc.bst whatif 447.50 corr 447.50
components/doxygen.bst whatif 509.55 corr 509.55
components/openssl.bst whatif 600.70 corr 600.70
```

The three unmeasured ones (`binary-seed-x86_64`, `buildsystem-make`, `buildsystem-cmake`): whatif refuses (`no_measured_duration`), correlate 0. `bga analyze`:

```text
    - components/_private/gcc-base.bst: up to 35.1 min off the finish (15.9% of the critical path)
    - bootstrap/gcc.bst: up to 30.6 min off the finish (13.9% of the critical path)
    - bootstrap/build/gcc-stage2.bst: up to 28.6 min off the finish (13.0% of the critical path)
    - components/_private/cmake-stage1.bst: up to 26.1 min off the finish (11.8% of the critical path)
    - bootstrap/build/gcc-stage1.bst: up to 22.5 min off the finish (10.2% of the critical path)
```

Page cards: doxygen `Realizable 8.5 min`; components/gettext `Realizable 34.1 s`; bootstrap/gcc `Worth fixing 30.6 min · Realizable 30.6 min`.

**Mutation table** — `python3 -m pytest -q tests/unit/test_one_saving_per_element.py`:

| mutation | reddened | count |
|---|---|---|
| `ranked = None` (the structural ceiling's own figure) | `test_the_structural_opportunities_are_whatifs_savings` | 1 failed, 3 passed |
| `REALIZABLE_SAVING_CANDIDATES = 8` | `test_analyze_publishes_…`, `test_correlate_publishes_…` | 2 failed, 2 passed |
| reverted | — | 4 passed |
