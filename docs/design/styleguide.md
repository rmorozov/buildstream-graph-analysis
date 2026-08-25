# The web report's visual contract

Written 2026-08-25 (round 41), from the user's brainstorm, while
Direction 15 is executed. This is the style guide for `bga view` and
its export: what a value renders as, what may be colored, what earns
emphasis, and what a drawing owes its reader. It exists for the same
reason the schemas do — so that consistency is a property of rules,
not of whoever wrote the last section.

Two standing constraints inherited from Direction 7 and never
suspended here: **the schema decides what things are** (a control is
chosen by declared shape and hints, not by which section is being
rendered), and **everything must survive the export** — a print, a
`file://` open, `filter: grayscale`, a pasted anchor. A pattern that
needs a server or a hover to mean anything is a served-mode
enhancement, never the meaning itself.

## 1. The mapping: published shape → control

The user's rule, adopted whole: **raw JSON on the page is a defect
unless it is deliberate.** What replaces it is this table — the
single dispatch every rendered node goes through. The left side is
what the schema (plus measured shape) says a value is; the right
side is the only control that may render it.

| published shape (+ hint) | control | notes |
|---|---|---|
| scalar + `bga:quantity` | formatted value with `data-raw` | unit per the quantity table; never a bare number |
| scalar enum (declared) | badge | text + tone; tone never alone (§4) |
| boolean / nullable presence | a sentence | "not captured" ≠ "zero" — absence is stated, never drawn |
| scalar + `description` | value + popover | the schema's sentence, on demand |
| array of objects | table (§3) | declared columns; distribution strip when §2 applies |
| short scalar array (≤ inline cap) | inline `code` list | existing rule, kept |
| long scalar array | count + folded list | count visible, fold labeled |
| object map, one key per element | table of key/value rows | Direction 12's rule — never a `<pre>` |
| small keyed object | definition list | the `pairs` pattern |
| ordered numeric series (`bga:series`) | **sparkline + one sentence** | §2; new hint, this guide introduces it |
| percentile/distribution object (`bga:distribution`) | **density strip + stated n** | §2; new hint |
| signed delta + `bga:direction` | signed value, tone by direction | existing, kept |
| severity list (`bga:severity`) | findings blocks | existing, kept |
| verdict + `verdict_kind` | banner, tone from enum | existing, kept |
| anything past the nesting cap | **the labeled fold** — count + label + JSON behind a click | the *one* deliberate raw-JSON site (`UX-277`), kept as the escape hatch |
| a section, on request | "view as JSON" toggle | deliberate, per section, for debugging and issue-pasting — this is the "on purpose" the rule allows |

Two consequences. A schema addition whose shape is in this table
renders correctly with **zero viewer changes** — that property
(UX-193) is the reason the mapping is by shape, not by key. And a
shape *not* in this table is a design task, not an improvisation:
it lands here first, with its control, then in the code.

## 2. Sparklines and density strips

Adopted, and widened from the user's proposal: any published value
that *is* a distribution or a series renders as its shape first and
its numbers second.

**Sparkline** — for ordered series (a metric over snapshots, a
history, a trend): fixed small geometry (the `UX-226` component is
the reference), no axes, no grid; endpoints and the extremum
hoverable; **one sentence beside it stating what it says** ("42
snapshots, drifting up since @2026-08-20"), from published values
only. Fewer than three points is a sentence, not a drawing — the
`UX-226` rule, now global.

**Density strip** — for distributions (percentiles over a
population): a horizontal strip with min → p50 → p95 → max marked,
`n` always printed beside it. Where the pipeline publishes the
percentiles (`store-aggregate/v1`, the element populations), the
strip renders them. Where a table's quantity column has no
published aggregate, the strip may be built **from the column's own
published `data-raw` values** — geometry is a reading of published
values, like sorting — under one boundary: **a self-built strip
prints no derived number.** Its labels are actual row values (min
and max are rows; hover names rows); percentile *positions* are
geometry only. The moment a derived percentile deserves printing,
it enters the published payload first, and the strip upgrades.

**The strip beside the table** (the user's fourth item, adopted):
every table longer than the row cap (§3) whose primary column is a
quantity carries the strip in its header region — the reader sees
the shape of 1,202 rows before scrolling any of them, and clicking
a region of the strip sets the column's threshold filter (served
mode; in the export the strip is static). This is the aggregate
the user asked to have "somewhere near the table", placed where
the eye already is.

## 3. Tables

The existing machinery (declared columns, sorting, text filter,
unit-aware thresholds, presets, top-N, copy, per-row Inspect,
nesting cap) is kept and this guide adds the reading rules:

- **Row cap by default.** A table renders its first N rows (N per
  table, argued, default 20) with "N of 1,202 — show all" — the
  page never silently renders four thousand rows again, and never
  silently hides any either. The strip (§2) is what makes the cap
  honest: the shape of the whole is visible before the fold.
- Numbers right-aligned, text left, units per cell (magnitude
  varies too much per column for header units), `data-raw` always.
- One tool row per table: filter, presets, top-N, copy — no
  per-table inventions; a new tool enters the guide first.
- Folding inside cells follows the nesting cap and is always
  labeled with a count — the `UX-277` rule, restated as law.

## 4. Color and emphasis: the budget

Grounded by running the palette validator on the current tokens
(round 41, transcripts in the round doc): the **dark set fails the
mark-lightness band** — three of four tokens are text-grade doing
fill work — and **amber↔green fails CVD separation in light mode**
(ΔE 3.6 protan, adjacent) while no ordering of four status hues
passes as adjacent categorical marks at all. The rules follow from
the measurements:

1. **bga's drawings have no categorical series.** Identity is text,
   magnitude is length, state is status tone. A drawing that wants
   multi-hue series must amend this guide first (and will be asked
   what a legend would say that direct labels cannot).
2. **One accent.** Interaction, links, the current focus, the band
   — one hue does all of it. A second accent is a defect.
3. **Status tones are reserved and never alone.** good/warn/bad
   carry a shape, marker or label in the same element, always —
   `UX-212`'s rule, promoted from the trend dots to the whole page.
   The measured CVD numbers are *why*: adjacent status hues are
   indistinguishable to some readers by construction.
4. **Text wears ink, never status tone.** Three ink levels — `--fg`
   for content, `--muted` for apparatus, one strong level for the
   current answer. Values stay ink-colored; the tone lives in the
   badge/border/marker beside them.
5. **Two token grades.** Text-grade tokens (contrast against
   surface for reading) and mark-grade tokens (inside the mark
   lightness band for fills) — the validator failure that motivated
   the split. No hex outside `style.css`; a new color is a token
   with a stated job or it does not exist.
6. **Emphasis is budgeted: one emphasized element per block.** The
   headline number is large once; a finding bolds its subject once;
   everything else is regular or muted. If two things in one block
   demand emphasis, the block is two blocks.

## 5. Dark first

Adopted: **dark becomes the design surface** — `:root` carries the
dark tokens, tuned first, and light becomes the override. Two
boundaries, challenged and kept deliberately:

- **Dark-first, not dark-only.** The export is attached, opened on
  unknown machines, and *printed* — a print stylesheet renders the
  light tokens on white with the drawings' non-color channels
  doing the work (§4.3 is what makes this free). A report that is
  only legible on one theme is evidence that stops at a screen.
- Both palettes hold the same token names and the same jobs; the
  themes differ in values, never in structure — and mark-grade
  tokens are validated per surface, not flipped automatically.

## 6. What a drawing owes its reader

Every visual element on the page carries, in order: **its answer as
one sentence** (from published values), the drawing, and its `n`.
No axes clutter on small multiples; no legend where direct text
does it; absence stated, never drawn as zero. A drawing whose
sentence cannot be written from published fields is a drawing the
pipeline is not ready for — publish first.

## 7. Enforcement

What keeps this true after the commit that lands it: the booted
real page contains **zero raw-JSON text nodes** outside the labeled
fold and the per-section JSON toggle (guard walks the DOM);
`JSON.stringify` in viewer modules is allowlisted to `data-raw`,
the copy path, and the fold; no hex literal outside `style.css`
(grep guard); status-tone class without a shape/marker/label
sibling reddens (booted check); sparkline/strip geometry asserts
against `data-raw` (the UX-196 discipline); and the conformance
checklist — shape in the table? sentence written? budget kept? —
joins the fixing guide for any task that touches the page.
