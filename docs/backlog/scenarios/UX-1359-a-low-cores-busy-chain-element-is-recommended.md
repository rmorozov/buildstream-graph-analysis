# UX-1359: a critical-path element with low cores busy and a real saving gets a recommendation

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R1, R2 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_low_cores_busy_chain_element_is_recommended.py`

## Motivation

`components/openssl.bst` holds 5.6% of the fdsdk critical path, runs at 1.49 of 4 cores busy, and `whatif` saves 600.7 s; its correlate row has `recommendations: []` and it is absent from "What to do next". Bootstrap gettext (0.54 cores, 7.3% of path) is likewise silent. Answering this is what correlate exists for (UX-51).

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

Every element on the critical path whose `whatif` saving is >= a stated share and whose cores busy is below a stated share of the granted width gets one recommendation line naming both readings.

## Out of Scope

Diagnosing why (install `-j1`, docs): that is UX-1358's serial stretch.

## Acceptance Test

On the fdsdk capture, openssl appears in "What to do next" with 1.49 cores and ~10 min. Mutation: drop the rule; the guard reds. The page's decision panel and openssl's element card carry the same line, read by the walker on this capture.

## Decision

The rule, stated: a critical-path element whose whatif saving is **at least 0.5% of the build** (`_WIDTH_UNUSED_SAVING_SHARE`) and whose cores busy is **under half its granted width** (`_WIDTH_UNUSED_SHARE`, over `resolved_jobs`) gets one `below-granted-width` line naming both readings. 0.5% sits under `_CHEAP_WIN_FLOOR`'s 1% on purpose: the line prints the price, so bootstrap gettext's 1.8 min is said at its true size, which is the field test's verdict #7.

- `bga/correlate.py`: `width_unused`, `impact_text`, `width_unused_text`; `_recommend` emits the line where no parallelism line already fired, and it replaces `already-compute-bound` when the element clears 1.25 cores but sits under half its width (openssl at 1.49 of 4). A group of them prints every element's two readings, never a range.
- `bga/findings.py`: analyze's `below-granted-width` finding (with `--plane2`), one detail line per element in correlate's words; its rule is in `bga/provenance.py`, so `--explain` prints it under the finding. Reader `recipe-author`. The decision panel carries it as the `build-it-wider` next step (reason = the top element's line, `bga correlate RUN`), which costs the page no bytes: a viewer block put the page half 57 B over `PAGE_BUDGET_B` (166,807 against 166,750), a budget this track does not move.
- The element card already renders `element_join[].recommendations`.
- `docs/guides/cli.md`: the finding row and the recommendation id (9 -> 10).

Guard: `tests/unit/test_a_low_cores_busy_chain_element_is_recommended.py` — a 3-element chain where `slow.bst` is 10% of the build at 1.49 of 4; correlate, the negative cases (2.0 of 4; 0.4% of the build), the compute-bound verdict, analyze's finding and rule, and the exported page's decision step and element card in Chromium.

## Outcome (2026-10-30)

**Gap measured** — `bga correlate /home/claude/fdsdk-cap/run /home/claude/fdsdk-cap/native-report.json --format json` after UX-1362:

```text
components/openssl.bst      save=0.0437 cores=1.49 of 4 req=1 recs=[]
bootstrap/base-sdk/gettext.bst save=0.0077 cores=0.54 of 4 req=1 recs=[]
components/python3.bst      save=0.0080 cores=1.86 of 4 req=1 recs=[]
```

`actionable`: gcc-base, gcc, gcc-stage2, cmake-stage1, gcc-stage1, bison, components/gettext, python3-minimal — no openssl.

**Close measured** — same command, text:

```text
  bootstrap/base-sdk/gettext.bst, components/openssl.bst, components/python3.bst (3 elements, 5-7% of the critical path each, 1.8-10.0 min apiece, 13.6 min together):
    - kept under half their granted cores busy: components/openssl.bst 1.49 of 4 (10.0 min), components/python3.bst 1.86 of 4 (1.8 min), bootstrap/base-sdk/gettext.bst 0.54 of 4 (1.8 min) — look at how they are built before what they build
```

`bga analyze … --plane2 native-report.json --explain`:

```text
  10.0 min on components/openssl.bst at 1.49 of 4 granted cores busy (+3 more chain elements)
    components/openssl.bst: holds 5.6% of the critical path and fixing it is worth 10.0 min (4.4% of the build), but kept 1.49 of its 4 granted cores busy (37.3%) — look at how it is built before what it builds
    (bison 0.90 of 4, python3 1.86 of 4, bootstrap/base-sdk/gettext 0.54 of 4: one line each)
    rule: _WIDTH_UNUSED_SHARE = 0.5 (<, bga/correlate.py)
```

Page (`bga view <snapshot>/run --reanalyse --export`, the capture with `plane2.json` beside it, Chromium 1243): decision panel step `build-it-wider` reads `components/openssl.bst: holds 5.6% … but kept 1.49 of its 4 granted cores busy (37.3%) — …`, `bga correlate …`, `from: 10.0 min on components/openssl.bst …`; openssl's card: `High holds 5.6% … 1.49 of its 4 granted cores busy (37.3%) …` and `Findings: 10.0 min on components/openssl.bst …`.

**Mutation table** — `python3 -m pytest -q tests/unit/test_a_low_cores_busy_chain_element_is_recommended.py`:

| mutation | reddened | count |
|---|---|---|
| `width_unused` returns False (drop the rule) | correlate, compute-bound, analyze finding, page | 4 failed, 1 passed |
| `elif not unused:` -> `else:` (compute-bound verdict stands) | correlate, compute-bound, analyze finding, page | 4 failed, 1 passed |
| `if unused and False:` in `compute_next_steps` (panel loses it) | page | 1 failed, 4 passed |
| reverted | — | 5 passed |
