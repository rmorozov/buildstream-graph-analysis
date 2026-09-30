# UX-1183: a traced element's binaries reach the page whole or counted

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1182 | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Finding: 1 of the review.

Screenshots `03-binary-cost-one-element.png`, `04-card-81-binaries-shows-1.png`. `finish(top_n=5)` in `tools/bst_native_build_tracer.py` keeps the top 5 by CPU and the top 5 by count. On the heavy page `layer12/mod058` exec'd 81 distinct binaries: `binary_cost` shows 9 rows (4 of them with CPU "none", from the by-count list) and the card shows 1 ("Dominant binary tar, 2.9%"). `gperf`: 3 elements ran it, 0 rows show it. `python3`: 8 elements ran it, 1 row shows it. The section's sentence says "45 binaries ran" against `by_binary`'s 81. The schema describes the section as "One row per element and binary Plane 2 saw it run". `wall_us` is published and not drawn. Breaks §1b and §1c. Task walk: "Which binaries did X run, and how long did each take?" - 9 of 81, dead end; "Which elements share binary Y?" - 0 elements shown where the log has 3.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a membership the capture saw is published whole or counted": drop `top_n` from `finish` for membership, keeping the ranked five for the card, and publish `binaries[]` per element: every (element, binary) pair Plane 2 saw, with calls, CPU and wall time. The card draws the rest as a bounded table. `binary_cost` gains the `wall_us` column. The section's sentence counts the capture (`by_binary`'s keys), not the rows kept. A permitted key under `plane2/v2`, no bump.

## Decision

Owner (Ruslan, 2026-09-30 19:04 ("your defaults looks good to try")), D3: publish every (element, binary) pair Plane 2 saw, with calls, CPU and wall time. Keep the top-5 lists for the card, and draw the rest bounded. Class: product.

## Out of Scope

The Plane 2 capture itself; the top-5 card lists, which stay (D3); the jump box's binary kind (`UX-1186`).

## Acceptance Test

`tests/unit/test_a_traced_elements_binaries_reach_the_page.py`, on `UX-1182`'s page (the heavy page until it lands): filtering `binary_cost` to the element with the most distinct binaries shows every one of them; filtering to a binary three elements ran returns 3 elements; the sentence's count equals the number of `by_binary` keys. Mutation: restore `top_n=5` on membership; the guard reds.

## Outcome

Open.
