# UX-207: the first screen is a decision, the rest is evidence

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-202 (the overview it compresses), UX-204 (the investigate transport the actions ride)

## Motivation

The round-23 external review's verdict, confirmed against the code:
the viewer is functionally rich but **report-shaped rather than
investigation-shaped** — the reader has to read too much before
knowing what deserves attention. The boot sequence
(`bga/viewer/app.js`, `boot()`) assembles: evidence header, overview,
band, verdict banners, summary, then every payload section in key
order, with the drawn chain, trend, blast and questions appended
after. Fourteen sections at the same visual level, and the TOC and
collapse controls compensate for density rather than solving
prioritization.

Meanwhile the answer the product is framed around — *"what should I
fix first, and what is it actually worth?"* — already exists in the
published payload and renders mid-list:

- the ranking is a finding (`bga/findings.py:890`,
  `blast-radius-ranking`) and the structural projections carry
  per-element savings — but they sit inside the generic findings
  section, in list order;
- the chain-bound/scheduler-bound diagnosis is computed
  (`bga/findings.py:974`) and then published only as a clause of one
  finding's sentence plus an evidence dict — no consumer can read it
  structurally;
- the evidence header (`renderEvidence`) spends six top-of-page rows
  on values that matter only when they are alarming, and an
  interrupted run's refusal renders **twice** — once from
  `renderVerdict` (`app.js`) and once from `renderEvidence`
  (`views.js`), the same sentence in two banners.

The review's rule, adopted: **first screen = decision, everything
else = evidence.**

## Required Fix

1. `analyze/v1` publishes a `headline` block — pipeline-side, in
   `bga/schemas.py` and the text renderer too, per Direction 7's
   rule that the viewer computes nothing:
   - `diagnosis`: an enum (`chain_bound` / `scheduler_bound` /
     `inconclusive`), the ratio it came from, and the one-sentence
     reading the CLI already prints;
   - the opportunity split as published fields: certified headroom
     (already published) beside a published scheduling-gap figure —
     not left as a subtraction for the page to do;
   - `top_actions`: ordered references (finding id, element uid,
     projected saving where a projection exists) into the findings
     that already carry the ranking.
2. The viewer renders the decision panel first: diagnosis sentence,
   the opportunity numbers, the top three actions each with its
   UX-204 investigate button. Reads `headline` only; absent
   `headline`, absent panel.
3. The evidence header compresses to one status line
   (`✓ high confidence · 100% task coverage · Plane 2 available`)
   with today's `<dl>` behind a `<details>`. A refusal
   (`incomplete_reason`, comparability) stays full-width and
   prominent — and renders **once**.
4. The overview compacts: the largest attribution segments stay
   visible, the remainder fold behind `<details>` — with **no
   viewer-summed "Other" row**; if a grouped figure is wanted it is
   published first.

## Out of Scope

- Dashboard stat-cards (the review argued against them; adopted —
  bga's numbers are relational).
- Any viewer-computed diagnosis, saving, or residual.
- Reordering or renaming payload keys.

## Acceptance Test

On the `examples/06` capture: the DOM order is decision panel →
status line → compact overview (asserted), the evidence `<dl>` is
inside a `<details>`, and the panel's diagnosis and actions match
the published `headline` (mutation: strip `headline` from the
payload → panel absent, page otherwise intact). On an interrupted
fixture exactly one `data-incomplete` banner exists (today's count:
two). The text renderer prints the same diagnosis sentence from the
same field. Schema round-trip validation covers `headline`; the
page-size guard (< 80,000 B) holds.
