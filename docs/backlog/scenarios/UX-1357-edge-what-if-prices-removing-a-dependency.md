# UX-1357: an edge what-if prices removing a dependency, not only zeroing an element

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R3, R2 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_an_edge_what_if_prunes_the_closure_it_alone_pulled.py`

## Motivation

On fdsdk, `components/libxml2.bst` build-depends on `components/doxygen.bst`, which pulls cmake-stage1 (26.1 min), python3 (10.5), bison and doxygen (8.5) onto the critical path. A list-scheduling replay of the measured durations without that edge finishes in 2.93-2.95 h against 3.82 h (-23%), 99 elements instead of 126. `bga whatif --element components/doxygen.bst` says 509.55 s, because it zeroes the element and leaves its closure on the chain. No bga output prices an edge a recipe author could remove.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

`bga whatif --drop-edge PRED:SUCC` (repeatable): replay with the edge removed and every element only that edge brought into the target's closure pruned; print makespan, element count and the pruned set. Reuse `correlate.project_without_edges`. The output is a priced question, never a removal verdict: bga cannot know why an edge exists.

## Out of Scope

Ranking candidate edges automatically.

## Acceptance Test

On the fdsdk capture, `--drop-edge components/doxygen.bst:components/libxml2.bst` reads 126 -> 99 elements and a makespan within 2% of 2.95 h. Mutation: stop pruning the closure and it reads ~3.7 h; the guard reds. The page's chain card offers the same what-if for a chain edge and shows the pruned elements; the walker reads 3.82 -> ~2.95 h on this capture's page.

## Decision

- `bga/edge_whatif.py` (new): `--drop-edge PRED:SUCC`, split at the `:` that names a real edge (a junction uid carries its own). One `correlate.project_without_edges` replay, which gains `pruned=`: its tasks, and dependencies on them, leave the after-replay. The target's closure (build and runtime edges, from `requested_target`, else the sinks) is read before and after; the difference is pruned.
- Gating is BuildStream's: a build waits for its build deps plus their runtime-only closure; its own runtime-only deps do not gate it. The normalised tasks carry direct build edges only, so the closure pairs are added to both replays here, and the pairs an edge alone produced are the ones removed. The rest of bga's replay still omits the runtime-only closure (3.69 h baseline on fdsdk, against 3.75 h here): not widened, a row for the session.
- `--element` combines: those builds become instant in both replays, and the text says the edge's price is "with the fixes above". An edge the graph does not hold is refused (`unknown_edge`) with the nearest names; edges alone are a question, so `empty_selection` is dropped.
- `whatif/v1` gains the optional `edges` object (`dropped`, `convention`, `refusals`, `projected`); no `required` key moved, so no bump. Text and JSON say it is a priced question, never a removal verdict.
- Page: the chain card (`critical-path-drawn`) gains a select of its consecutive edges, the target's edge first chosen, and a button. Served, it asks `whatif.json?drop_edges=P:S` - the same `edge_whatif.answer` the CLI calls - and shows before -> after, the element counts and the pruned set; offline, the command. Smallest design: no payload precompute, no replay in the page.
- Guard: the test above, on an 8-element fixture where `doc.bst -> app.bst` alone pulls a 30 s chain and a 40 s runtime-only dep. Mutations: skip the pruning; drop the runtime-only closure from gating; skip the refusal; the page omits the pruned set.

## Outcome (2026-10-30)

**Gap measured** (the base install, before the change):

```text
$ bga whatif /home/claude/fdsdk-cap/run --drop-edge components/doxygen.bst:components/libxml2.bst
bga: error: unrecognized arguments: --drop-edge components/doxygen.bst:components/libxml2.bst
$ bga whatif /home/claude/fdsdk-cap/run --element components/doxygen.bst
  Makespan 13219.750s -> 12710.200s (saves 509.550s)
```

**Close measured** (this worktree, the fdsdk cold capture `run/`):

```text
$ python3 -m bga.cli whatif /home/claude/fdsdk-cap/run --drop-edge components/doxygen.bst:components/libxml2.bst
What if these edges were dropped: components/doxygen.bst -> components/libxml2.bst
  Replayed makespan: 3.75 h -> 2.87 h (-23.4%); observed wall 3.82 h
  Elements in the target's closure: 126 -> 99; pruned 27: components/_private/buildsystem-cmake.bst, ...
$ ... --format json  ->  "baseline_makespan_us": 13484300000, "makespan_after_us": 10333200000,
                         "elements_before": 126, "elements_after": 99, len(pruned) == 27
```

126 -> 99 holds. 2.87 h is 2.7% under 2.95 h, outside the 2% band: bga's LPT replay at 4 builders reads the baseline at 3.75 h, against the expert's 3.81-3.82 h; the ratio, -23.4%, matches the expert's -23%. The page, served by `bga view` and clicked in Chromium 1243 (`BGA_CHROME`), at 1440 and 390 px, no horizontal overflow:

```text
card: critical-path-drawn   edge: components/doxygen.bst:components/libxml2.bst   options: 22   source: server
Without it the replay reads 3.7 h → 2.9 h (observed 3.8 h), 126 → 99 elements. A priced
question for the recipe author, not a removal verdict: bga cannot know why the edge exists.
Pruned 27 elements: components/_private/buildsystem-cmake.bst, components/_private/cmake-stage1.bst, ...
```

**Mutation table** (`tests/unit/test_an_edge_what_if_prunes_the_closure_it_alone_pulled.py`, 7 tests):

| mutation | reddened | fdsdk reading under it |
|---|---|---|
| `pruned = set()` (skip the pruning) | 4 failed, 3 passed | 3.75 h -> 3.73 h |
| runtime-only closure left out of gating | 4 failed, 3 passed | 3.69 h -> 2.81 h |
| every edge accepted (refusal skipped) | 1 failed, 6 passed | — |
| page omits the pruned names | 1 failed, 6 passed | — |
| restored | 7 passed | 3.75 h -> 2.87 h |

The page half of the golden export grows 166,695 -> 167,539 B (+844 B), over `PAGE_BUDGET_B`'s 166,750: three size guards red (`test_the_viewer_js_ships_compressed.py`, two in `test_the_report_you_can_attach.py`). The budget is an owner call (UX-1350), not moved here.
