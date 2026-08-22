# UX-214: one verdict vocabulary, published as one

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-203 (the trend that grew the second chain), UX-201 (the enum it should share), UX-190

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
