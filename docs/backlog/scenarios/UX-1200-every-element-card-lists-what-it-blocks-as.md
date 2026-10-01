# UX-1200: every element card lists what it blocks, as links, with one count

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

0 of 24 ranked element cards draw Blocks or Depends on (payload fan_in.dependents: layer12/mod058 = 6, layer16/mod006 = 4). The on-demand card layer00/mod017 draws "Blocks: layer01/mod016.bst, layer01/mod044.bst" as plain code text, not links, beside "Rebuilds 807". The Focus investigation for layer12/mod058 says "Blocks (chain): layer13/mod058.bst" (1) against 6, and "Rebuilds if changed 254". "+N more" never draws on a real page (walk N8, D2).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Ranked and on-demand cards list Blocks and Depends on from the payload, each an element link; Blocks counts agree between the card and the investigation; "+N more" draws past the bound on a real page.

## Out of Scope

The deep-leaf bound (`UX-1187`).

## Acceptance Test

layer12/mod058's ranked card lists 6 Blocks links and its investigation says 6; a page with a node over the bound draws "+N more"; a guard in `test_an_element_view_answers_whole.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
