# UX-566: two "recommended" Parts describe a tool that was never built that way

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the reader who opens the spec's tail for the report or the tree | **Topic:** docs

## Motivation

```text
Part 38 (specification.md:2349-2416)   11 upper-case report chapters — RECOMMENDATIONS, REBUILD LEVERAGE, TRACE QUALITY…
golden text report                      Key Findings / Confidence / Certified Floors / Attribution Breakdown / CPU Utilisation /
                                        Advanced Diagnostics / Structural Analysis / Plane 2 / Next
Part 39 (specification.md:2427-2489)   32 modules — reachability.py, depth.py, dominators.py, slack.py, ready_queue.py, retry.py, timeline.py…
tree                                    12 modules in those packages; bga/structural/ (6 files) and validation/provenance.py unnamed
Part 37                                 `--cold` requires `--history-dir`, which the spec never names
specification.md:1714                   "additionalProperties is true in all three" — there are eight printable contracts
```

The spec's header disclaims Parts 38-40 as recommended, and the
house rule keeps the body unedited; nothing tells a reader which
Parts are the design and which are the archaeology.

## Required Fix

A Part 32 registry note listing the Parts that are advisory and
superseded by the tree (37's flag, 38, 39, 40, the "all three"
sentence), each with the document that is current — so the spec
carries its own map of what to trust. No body edit.

## Out of Scope

- Rewriting the Parts — the body is ground truth and stays unedited (§3.12); the registry note is the whole change.

## Acceptance Test

The note exists and names each Part; `test_a_counted_figure_is_derived`
covers the "all three" sentence.
