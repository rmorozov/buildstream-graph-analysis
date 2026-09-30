# UX-1159: key paths and schema descriptions reach reader text

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-154 walk, items 8, 9 and 10; the UX-1141 and UX-1144 residue (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

Key paths in `<code>` serve as reader labels ("Threshold headline.chain_share < 0.9", evidence "headline.chain_share 42.4%", "Paths resolve against analyze/v6"), pinned by `test_why_bga_believes_what_it_believes` and `test_the_provenance_names_its_rule`; long schema descriptions name `host_cpu_count`, `native_max_jobs`, `cpu_budget`, `avg_fanin`, `avg_fanout`, `ru_maxrss`, `max_concurrency` and no guard sees a description absent from the fixtures; "Records embedded no"; `format.js` quantity/duration/bytes and `views.js` history rows draw a dash for null; 146 " - " dashes in prose. Whether `T∞`, `LB`, `T_C` should carry plain-language names is a question, not a defect (UX-1144 decided the symbols).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A key path stays where a reader copies it, not where one reads it; a schema-walking check sees every description; the symbol question is put to the session.

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

A guard that walks `schemas.schema(name)` finds no snake_case key in a description, and no reader-text node is a key path outside a copy control. Mutation: restore the defect, and the new guard reds.

## Outcome

Open.
