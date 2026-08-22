# UX-207: the first screen is a decision, the rest is evidence

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-202 (the overview it compresses), UX-204 (the investigate transport the actions ride)

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

## Outcome

All four items. The load-bearing decision was where the diagnosis
lives, and the answer is Python.

**1. `headline` is published.** `diagnose()` decides chain-boundness in
`findings.py`, beside the ratio that decides it. That decision has
existed since `UX-65`, but as a **local `bool` inside
`compute_findings`** that reached the outside world only as the clause
" - this build is chain-bound, not scheduler-bound" glued onto one
finding's title — so a consumer wanting to *branch* on it had to
string-match a sentence. `compute_findings` now reads `diagnose()`
rather than recomputing the ratio, and a guard asserts
`CHAIN_BOUND_RATIO` appears in exactly one comparison.

The block carries the enum, the ratio, the threshold, the sentence, the
opportunity split and the actions:

| field | on the golden run | on `examples/06` |
| --- | --- | --- |
| `diagnosis` | `scheduler_bound` | `chain_bound` |
| `chain_ratio` | 0.875 | 0.936 |
| `scheduling_gap_us` | 2,000 | 2,933,000 |
| `top_actions` | 3, by `downstream_count` | 3, by `saving_us` (core.bst 12.05 s) |

**Two committed fixtures that answer differently** — which is the point:
the golden run is scheduler-bound and falls back to the blast-radius
ranking, the real capture is chain-bound and ranks by realizable
saving. A guard that only ever saw one branch would not be guarding the
branch. Both run on a fresh clone (`UX-213`'s rule, applied from the
start rather than retrofitted).

`scheduling_gap_us` is a *field* because the Required Fix says so —
"not left as a subtraction for the page to do" — and `top_actions` are
**references**, carrying `finding_id` so the panel can send a reader to
the reasoning rather than restating it. A saving nobody projected is
absent rather than zero.

**2. The panel reads.** And proving that it reads took building the
case, not writing the mutation: recomputing `t_infinity / total` in the
viewer **reddened nothing**, because on both fixtures the recomputation
agrees with the published answer — a deriving page and a reading page
are indistinguishable there. They are only told apart by a payload
where the two disagree, so there is now one: floors saying 0.95,
`diagnosis` saying `scheduler_bound`. A reading page shows what was
published; a second analyzer overrules the pipeline. That is
`UX-179`'s lesson, met again in a new place.

**3. The evidence header compresses, and the refusal renders once.**
The duplicate was real and measured: **two `data-incomplete` nodes** on
an interrupted fixture, the same claim in different words from
`renderVerdict` and `renderEvidence`. The banner now belongs to
`renderVerdict` alone — the header is also the part a reader may have
collapsed, which is the worst place for the one sentence they must not
miss — and it draws its wording from `INCOMPLETE`, where `UX-202` put
the three sentences and where the `RunContext` guard still points. The
`<dl>` moved behind a `<details>` under a one-line status
(`✓ high confidence · 100% task coverage · Plane 2: 813 processes`),
whose band comes from the payload, never from a threshold applied here.

**4. The overview compacts with no "Other" row.** The four largest
segments stay; the tail folds. The guard is the honest form of the
rule: every bar's `data-field` must *resolve in the payload* — a summed
row could not, which is exactly why that is the check rather than a
prefix match.

Tests: 37 new, plus four repointed to the banner's new home. Six
mutations, each red. A seventh was **discarded rather than counted**
(recomputing the diagnosis) until the discriminating payload existed to
make it meaningful.

**A guard of the project's own caught the gap while this was in
flight:** `test_the_pin_describes_the_real_output` failed with "new
top-level key(s) ['headline'] — add them to `ANALYZE_FULL_KEYS`". It
was right, and `headline` is in the list.

**Deviation from the Required Fix:** none. Stat-cards stay declined and
no viewer-computed diagnosis, saving or residual was added.
