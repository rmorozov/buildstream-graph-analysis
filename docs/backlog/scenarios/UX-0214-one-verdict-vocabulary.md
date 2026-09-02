# UX-214: one verdict vocabulary, published as one

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-203 (the trend that grew the second chain), UX-201 (the enum it should share), UX-190 | **Topic:** contracts

## Motivation

Round 23's verification found the trend's verdict colouring is a
**second, divergent verdict chain**. `_mark_verdicts`
(`tools/bga_snapshot.py`) classifies each snapshot purely on band
edges and emits `"within_band"` — a value outside
`schemas.VERDICT_KINDS` — with none of compare's significance or
disputed-region branches. Consequence, on the exact case the band
view exists to teach: a run below `band_low` but inside the
baseline set's observed range colours **improved** on the trend,
where `bga compare` on the same pair answers
`within_observed_range` and declines the claim. UX-170's disputed
region, silently re-litigated by a dot. The UX-203 log's "the
colouring cannot disagree with what `bga compare` would say" is an
over-claim — only `compute_band` is shared. (`style.css` styles
`verdict-within_band` deliberately: the split is intentional and
nowhere documented.)

Beside it, the smaller contract gap: `compare/v1` publishes
`verdict_kind` as `type: ["string", "null"]` with **no `enum`
keyword** — the closed set lives in the Python constant and the
viewer's map, so the external consumer UX-201 promised the enum to
never sees it.

## Required Fix

One classification. The store rows get their `verdict_kind` from
the same code path compare uses (significance, disputed region and
all), or a shared function both call; `within_band` either joins
`VERDICT_KINDS` with a definition or disappears in favour of the
existing kinds. The published schemas carry the closed set as a
real `enum` — in `compare/v1` and in `store/v1`'s rows — so the
round-trip guard can hold every emitted value inside it.

## Out of Scope

- Changing what any verdict means, or compare's thresholds.
- The trend drawing itself (UX-212 covers its encodings).

## Acceptance Test

On a store whose latest run sits below the band but inside the
observed extent, the trend dot carries the same `verdict_kind`
`bga compare` reports for that pair (the disputed-region case
asserted end to end). The emitted `compare/v1` and `store/v1`
schemas contain an `enum` for `verdict_kind`; the golden round-trip
guard reddens when a payload emits a value outside it (mutation:
emit `within_band` without declaring it → red).

## Outcome

One chain, and the published set is a real `enum`.

**The disagreement, measured before it was fixed.** It takes a
deliberately skewed baseline set to reach the disputed region, so here
is one: `[100, 100, 100, 100, 200]`. MAD collapses to zero, the band
widens only to the fixed 5% floor — `[99, 101]` — and the set's own high
edge ends up *outside* the band it produced (`edges_outside_band: 1`).

| candidate | old store rule | `bga compare` |
| --- | --- | --- |
| 150 | **regressed** | `within_observed_range` |
| 101 | `within_band` | `no_significant_change` |
| 90 | improved | improved |

The 150 row is the whole item: outside the band, inside the range the
baselines themselves reached, so the set cannot support a claim — and
the trend coloured it a regression anyway.

**`UX-203`'s log said "the colouring cannot disagree with what `bga
compare` would say about the same pair". That was mine, and it was an
over-claim** — only `compute_band` was shared. `classify_against_band`
is what makes the sentence true, and both callers now use it.

**What was deliberately *not* unified:** the direction. Whether a band
supports a claim at all is one question; which way is another, and the
two callers answer it from different evidence — `bga compare` has a
signed delta against a named baseline run, the store's trend has only
the set. So the direction is passed in (`delta_us`), and compare's
verdicts mean exactly what they meant. The Out of Scope line says
"changing what any verdict means" is not this item, and it did not.

`widen_band` was extracted alongside, because judging against raw band
edges rather than the widened ones is the same class of divergence one
step earlier. The store widens with the median as its reference total —
what "the baseline" means for a set rather than for one positional run.

**The schemas carry the closed set now**, in `compare/v1` and in
`store/v1`'s rows, built from `VERDICT_KINDS` rather than spelled out —
a guard counts the two occurrences of `list(VERDICT_KINDS)` so a third
copy cannot appear. `within_band` is gone from the code, the schema and
the stylesheet, and a guard asserts `style.css` styles no verdict kind
nothing publishes.

Tests: 11 new. Three mutations, each red — the acceptance's named one
(emit `within_band` without declaring it) reddens four, including the
`jsonschema` round-trip over a real store listing.

**Two guards elsewhere were updated rather than deleted**, both mine
from earlier rounds: a round-22 assertion listing `within_band` among
the acceptable kinds now asserts membership of `VERDICT_KINDS`, and the
docs guard that *scraped* `compare.py` for `if band_disputed:` now
reads `VERDICT_SENTENCES` — a better source than a slice of source
text, and still read rather than pinned.
