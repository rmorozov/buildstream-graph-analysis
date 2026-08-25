# Audit round 41: the page gets a visual contract

Run on 2026-08-25, while the sibling executes Direction 15 — main
carries only round 40's filings, so there is no landing to verify
this round; it is a design round, from the user's brainstorm: no
raw JSON that is not deliberate, sparklines widely adopted, a
distribution beside anything that lists many elements, a
JSON-pattern-to-control mapping, rules for emphasis and color, dark
theme first.

## What was measured before anything was ruled

The viewer's ground truth first: `UX-267` already replaced the
wall-of-`<pre>` with shape-chosen rendering (34 cells, 32,393
characters of raw JSON on a 44-element run, measured then), leaving
exactly one deliberate raw-JSON site — the labeled deep-fold. One
sparkline exists (`UX-226`); no density strip anywhere. The hint
vocabulary is nine entries strong. The palette had never been
validated, so round 41 ran the categorical validator on both token
sets: **three of the four dark tokens sit above the mark-lightness
band** (text-grade colors doing fill work in every bar and dot),
and **amber↔green fails CVD separation in light mode** (ΔE 3.6
protan, adjacent) — while no ordering of the four status hues can
pass as adjacent categorical marks at all. Those two measurements
became rules rather than adjectives.

## The contract

`docs/design/styleguide.md` — seven sections: the shape→control
mapping (§1, the user's "no raw JSON" as a dispatch table with two
named escapes: the labeled fold and a per-section view-as-JSON
toggle); sparklines and density strips (§2, with the strip beside
every capped table); table reading rules (§3 — the sibling's
presets and folds kept, a default row cap added, no new mechanism
invented); the color and emphasis budget (§4 — no categorical
series in bga drawings, one accent, status never without a shape,
two grades of token, one emphasis per block); dark first (§5);
what a drawing owes its reader (§6 — its answer as one sentence,
and its n); enforcement (§7).

## Challenged, per the user's invitation

- **Dark-only** → dark-*first*: `:root` becomes the dark surface,
  but the export is attached and printed — a print stylesheet
  renders light, paid for by §4's non-color channels.
- **The density strip's arithmetic boundary**: a strip built from a
  column's own published `data-raw` values is geometry — a reading
  of published values, like sorting — but it may print **no derived
  number**. Labels are actual row values; a percentile worth
  printing enters the payload first. The no-arithmetic rule
  survives with its line drawn precisely where presentation ends.
- **Tables**: the user offered to replace the fold/preset scheme;
  the audit kept it — the friction was never the folds, it was
  walls of rows with no shape. The row cap plus the header strip
  answer that without a third mechanism.

## Filed

`UX-302` (the mapping made law, plus the toggle), `UX-303`
(sparklines and strips, `bga:series`/`bga:distribution`), `UX-304`
(dark first, two token grades, validated values), `UX-305` (the
emphasis budget and the conformance pass), `UX-306` (the guide
wired into the tree). Direction 16 records the contract's place.

## Landed

All five items shipped in the order above (`UX-302`, `UX-304`,
`UX-303`, `UX-305`, `UX-306`), each with its falsification round in
its own log. Three things the round turned up that the filings did
not predict, recorded here because they are the round's real
findings:

- **A guard from one item caught the next.** `UX-304`'s §4.3 check
  reddened on `UX-303`'s first draft, which coloured a sparkline's
  peak and a p95 tick amber. It was right — a peak is a position and
  a percentile is not a verdict — and they are told apart by size and
  dash instead.
- **A `var()` fallback is a second palette, and it hides the first.**
  `UX-305`'s pass found `var(--accent, #4a7ebb)` eight times;
  `.horizon-bar` had been filling with a text-grade token straight
  through `UX-304`'s guard, because the guard matched `var(--accent)`
  and the fallback was not that string. Removing the fallbacks made
  the existing guard fire.
- **The export ships the source commentary.** `UX-303` took the page
  from 183 KB to 197 KB and tripped `UX-287`'s data-dwarfs-the-page
  ratio at 3.90x. 175 KB of the 196 KB page is commented JavaScript,
  because `--export` inlines modules verbatim. Filed as `UX-307`
  rather than absorbed.

## Standing

Direction 15 outranks all of this — the user cannot open their
capture until `UX-296`/`UX-297` land, and nothing here blocks on
anything there. When the sibling surfaces: `UX-302` first (it is
mostly guards over won ground), `UX-304` next (the palette is
measured wrong today), then `UX-303`, `UX-305`, `UX-306`. The
style guide governs new work immediately either way: it costs a
read, and it is the difference between a page that stays coherent
and one that needs a round 41 every ten rounds.
