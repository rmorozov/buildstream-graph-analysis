# The web report's visual contract

Written 2026-08-25 (round 41), from the user's brainstorm, while
Direction 15 is executed. This is the style guide for `bga view` and
its export: what a value renders as, what may be colored, what earns
emphasis, and what a drawing owes its reader. It exists for the same
reason the schemas do — so that consistency is a property of rules,
not of whoever wrote the last section.

**Scope, and its sibling** (`UX-306`). This document governs the
**web report**. The repository's *documents* have their own guide —
[`contributing/style-guide.md`](../contributing/style-guide.md) —
and the two do not overlap: nothing here decides a paragraph, and
nothing there decides a pixel. The checklist that routes a change to
whichever applies is item 6 of
[`contributing/fixing-guide.md`](../contributing/fixing-guide.md) §2.

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
| array of arrays | table of positional columns | `UX-290`; declared `bga:columns` name them, otherwise `#1`/`#2` |
| short scalar array (≤ inline cap) | inline `code` list | existing rule, kept |
| long scalar array | count + folded list | count visible, fold labeled |
| object map, one key per element | table of key/value rows | Direction 12's rule — never a `<pre>` |
| small keyed object | definition list | the `pairs` pattern |
| ordered numeric series (`bga:series`) | **sparkline + one sentence** | §2; the hint's value names the unit of one step, so the sentence can say it (`UX-303`) |
| percentile/distribution object (`bga:distribution`) | **density strip + stated n** | §2; the hint's value names the key holding the sample count (`UX-303`) |
| signed delta + `bga:direction` | signed value, tone by direction | existing, kept |
| severity list (`bga:severity`) | findings blocks | existing, kept |
| verdict + `verdict_kind` | banner, tone from enum | existing, kept |
| anything past the nesting cap | **the labeled fold** — count + label + JSON behind a click | the first of the two deliberate raw-JSON sites (`UX-277`), kept as the escape hatch |
| a section, on request | "view as JSON" toggle | deliberate, per section, for debugging and issue-pasting — this is the "on purpose" the rule allows |
| a **mixed** array (objects and scalars together) | *no control* — the labeled fold, and a console warning | `UX-302`: deliberately not a row. The old code improvised one, and rendered `[object Object], 2` |

Two consequences. A schema addition whose shape is in this table
renders correctly with **zero viewer changes** — that property
(UX-193) is the reason the mapping is by shape, not by key. And a
shape *not* in this table is a design task, not an improvisation:
it lands here first, with its control, then in the code.

**Where the drawings live** (`UX-303`). `bga/viewer/drawings.js`
holds §2's two controls — `sparkline()` and the two strips — and it
imports nothing and takes its formatter, so a guard can drive it with
no page. `bga:series` and `bga:distribution` are declared in
`bga/schemas.py`; `tests/unit/test_the_shape_before_the_rows.py`
asserts every drawing's geometry against the values it was handed.

**Where the table lives** (`UX-302`). `bga/viewer/shapes.js` is this
table as code: `classify(value, …)` returns the control's name, and
every render path asks it rather than testing shapes itself. A shape
it cannot place returns `UNMAPPED`, which renders as the labeled fold
*and* warns on the console naming the payload path — the gap is
visible without the reader being shown nothing. The two deliberate
raw-JSON sites are the fold's `<p class="full-text">` and the
per-section "view as JSON" toggle's `data-raw-json`;
`tests/unit/test_the_mapping_is_law.py` boots the golden and
`macro_micro` pages, walks every text node, and fails on a third.

## 1a. The hint vocabulary

Twelve hints, and this table is the one place they are all written
down (`UX-306`). Each names what a schema *declares* about a value;
§1 above is what the page does with it. A hint the schemas emit and
this table does not name is a hint whose meaning lives only in code,
which is the drift `UX-214` and `UX-273` both exist to prevent —
`tests/unit/test_the_contract_names_its_vocabulary.py` holds the two
sets equal in both directions.

| hint | what the schema declares | read by |
|---|---|---|
| `bga:quantity` | the unit a number is in, so it formats and a threshold parses | every value, every column, `parseThreshold` |
| `bga:question` | the question a section answers, in the reader's words | the heading, the rail, the chapter table |
| `bga:rail` | which part of the argument a section belongs to | the rail's fallback grouping (`chapters.js` decides first) |
| `bga:role` | that a column holds element uids | the generic Inspect link on every row |
| `bga:markers` | the shape vocabulary a verdict enum draws with | the trend, the history sparkline (§4.3's non-colour channel) |
| `bga:severity` | that an array carries findings | the findings blocks |
| `bga:columns` | which columns an array of objects has, in what order | every table, and `UX-290`'s named tuples |
| `bga:direction` | what the sign of a delta means | the delta's marker and tone |
| `bga:presets` | a named view over one table — rows, columns, order, bound | the view selector and the rail's sub-entries |
| `bga:series` | that an array is an ordered series, and the unit of one step | the sparkline and its sentence (§2) |
| `bga:distribution` | that an object publishes percentiles, and where it counts | the density strip and its stated `n` (§2) |
| `bga:inline` | that this value's sentence stays beside it rather than behind its `?` — `name` or `caveat` (§4a) | `describedTerm`, which then draws no door |

Two properties this table is here to keep. **A hint is a declaration,
never a guess**: the page reads what the schema says a value is and
falls back to name-sniffing only where the schema says nothing, which
is a schema gap rather than a feature (`UX-201`). And **a vocabulary
kept twice diverges**: the shapes, the rails and the verdict markers
are all declared in `bga/schemas.py` and read by the viewer, never
re-listed in JavaScript.

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

## 2a. Drawing grades and the size scale (round 44)

The field found §2's "fixed small geometry" over-applied: one size
served both the sparkline beside a table cell and the drawing that
*is* a section's whole answer, and at annotation size the answers
were invisible — the blast-radius distribution, the store diagram
and the element-duration distribution all drew at 20 viewBox units
and said nothing. The token lesson (§4.5) again: one grade cannot do
two jobs.

- **Annotation grade** — a drawing beside something else (a history
  sparkline in an element section, a strip in a table header): the
  §2 small geometry, unchanged. Its reading is "shape at a glance";
  its numbers are one hover away.
- **Exhibit grade** — a drawing that is the section's answer (a
  distribution the section exists to show, the store diagram, the
  graph shape): container width, height from the size scale,
  readable tick labels, and **always paired with its table twin** —
  an "as table" toggle rendering the same published values as a §3
  table, so the drawing never hoards data a reader wants as rows.
- **The size scale**: drawing heights and type sizes come from a
  small token scale in `style.css`, not from per-drawing constants
  — the normalization instrument. A drawing is annotation grade or
  exhibit grade; there is no third size, and a guard holds geometry
  to the scale.
- The grade is declared where the drawing is placed (the renderer
  knows whether it is the section's answer), never guessed from
  data.

## 2b. Apparatus in its place (round 44)

Three placement rules the field pass earned:

1. **A control's explanation lives with the control.** The
   save-the-trace sentence belongs inside the Perfetto action
   group, not in the header two blocks above it. Nothing explains
   a control from under a different heading.
2. **The header carries identity only** — run name, stamp, verdict
   state — within a stated vertical budget (measured in lines, in
   the guard). Actions and their apparatus live in the actions
   group; prose lives in sections.
3. **A described value shows its affordance.** §1 gave described
   values a popover; discovery was hover archaeology. A value whose
   schema carries a `description` renders a visible marker (the
   `?`), and the description opens *beside the value* — to its
   right where the row has room, below it where it does not. In
   print and export the marker survives and the description renders
   inline-on-open state only; hover is never the only door (§4.3's
   rule, applied to prose).

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

### 3a. The depth budget and table focus (round 44)

The field report: tables nest several levels deep, the reader
cannot tell how deep the rabbit hole goes, and a nested table's own
scroll does not work inside a scrolling parent. Three rules:

1. **Depth is announced.** A cell that folds deeper content states
   what is below it — "2 levels, 34 rows" — before any click. The
   unknown-depth rabbit hole is the defect; the count is the fix.
2. **One nested level renders inline.** Deeper than that, the fold
   does not open in place: it opens in **table focus** — the
   nested table takes the content column's full width as a plain
   in-flow section (its breadcrumb naming the path back), and the
   parent collapses behind it. One mechanism, deliberately not an
   overlay or drawer (round 24's export-survivability argument
   stands): focus is served-mode state like `UX-222`'s, the export
   renders folds with counts, and nothing about the meaning needs
   the mechanism.
3. **Every capped or nested table offers focus explicitly** — the
   user's enlarge affordance: one control, "expand this table",
   entering the same focus state. Nested scrollboxes are abolished
   rather than fixed: a table scrolls only when it is the widest
   thing on screen, which in focus it always is.

### 3b. The click budget (round 44)

Navigation cost is measured, not felt: from a chapter's rail entry,
any section's content is reachable in **at most two interactions**
(open chapter, open section), and the walk that measures the worst
path is a guard, not an aspiration. A structure change that pushes
a third click into the common path reddens before a reader meets
it. Folds inside content (the labeled fold, the chain's middle) do
not count against the budget — they are depth, not navigation — but
their counts must be visible (§3a.1), so the reader spends clicks
knowingly.

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

**Where the tokens live, and how to re-run the validation**
(`UX-304`). `bga/viewer/style.css` holds every color the product
has — `:root` is the dark set, `@media (prefers-color-scheme: light)`
the override (it also matches a reader who expressed no preference,
so an unset browser is unchanged), and `@media print` the light
tokens on white. `tests/palette.py` is the validator: WCAG luminance
and contrast, CIE L*, ΔE2000, and the Viénot/Brettel/Mollon
dichromat projection, no dependencies.
`tests/unit/test_the_palette_is_validated.py` runs it and pins the
bands — mark-grade at ≥3:1 and L* 45–70 on dark, 35–60 on light;
text-grade at ≥4.5:1 — checks that fills name mark tokens and text
names text tokens, refuses a hex literal anywhere outside the
stylesheet, and holds every status-toned rule against a list naming
its non-color channel.

## 6. What a drawing owes its reader

Every visual element on the page carries, in order: **its answer as
one sentence** (from published values), the drawing, and its `n`.
No axes clutter on small multiples; no legend where direct text
does it; absence stated, never drawn as zero. A drawing whose
sentence cannot be written from published fields is a drawing the
pipeline is not ready for — publish first.

## 3c. The distance budget (round 52)

§3b's click budget is measured and met, and the round-52 census found
what it does not see. Clicks from first paint to each thing a reader
comes for, on `macro_micro`:

```text
                              clicks   screens down
the verdict sentence               0            0.3
a Perfetto query                   1            5.9
the element table                  0            6.8
confidence                         0           18.3
the run identity                   0           19.6
```

Zero clicks, because almost nothing is folded — 51 `details`, 3 open,
and every *section* permanently expanded. The budget was satisfied by
converting navigation into an 18,148 px scroll.

**So distance is a budget too.** A click is directed: the reader names
what they want and arrives. A screen of scroll is a search: they do not
know how far, and pass everything they did not ask for. A structure
change may spend one currency to buy the other, and the guard has to
see both or it will keep buying the invisible one.

The rule, with the numbers `UX-347` set against the page as it stands
after §4a's note removal:

- the document a reader lands on is at most **10 screens at 1440x900**;
- every chapter's question sits within **8 screens** of the top;
- and a chapter's first section begins within **half a screen** of its
  own heading.

All three are asserted in the same guard that holds the click budget,
so a trade shows up on the side it was paid from, and the guard's
failure message publishes the walk to all eight destinations in *both*
currencies.

**The lever is folding by chapter.** Every chapter but the first opens
to its question, one line answering it from published fields, and a
control naming how many sections are behind it; the first chapter is
the decision and stays open. Measured: the document went 11.6 → 4.1
screens (golden) and 22.7 → 6.6 (macro_micro), `confidence` from 18.3
screens down to 6.3, the run identity from 19.6 to 6.7 — and no walk
grew a click, because every way into a section opens the chapter
holding it.

A chapter's one-line answer is **read from what the document already
publishes** (`chapters.js`'s `answer`), never computed beside it: a
summary that derived its own numbers would be a second pipeline,
disagreeing quietly. A chapter whose fields are absent folds with its
question and its count and no sentence, which is the honest answer for
a run that cannot support one.

## 4a. Where a sentence lives (round 52)

`UX-220` gave every declared quantity a sentence from the contract.
Round 52 measured where they ended up: **43% of the golden page's words
and 37% of `macro_micro`'s** are those sentences, printed beside every
value on every run, while the same sentence sits behind a `?` door on
the same line.

(The round's first figure was 67-72%. It counted `.pairs dd` whole —
the value cell, so every number on the page counted as prose. The
figures above count `[data-role="description"]` and are the ones
`UX-346` was verified against. The instrument was the defect, twice in
one round: see `UX-343`'s census.)

A description is **reference**, and §2b already decided where reference
goes: on demand, near what it explains, not in the reading path. The
sentence lives on the door.

**And the door has to close.** `UX-317` built the door in round 41 and
it never shut: `[hidden]` is a UA rule at specificity (0,0,0) and
`.description { display: block }` beats it, so the sentence rendered
whatever the `?` said. A control whose state nothing renders is not a
control — before trusting a disclosure, measure the *computed style and
the box*, never the attribute you set.

Two exceptions stay inline, declared in the contract as `bga:inline`
(`name` or `caveat`) so the page cannot decide case by case:

- a value whose *name* invites a reading it does not have —
  `useful_share` is a share of capacity, not of wall-clock — or invites
  none at all, like `t_infinity_observed`;
- a **caveat** rather than a description: the "this is a ranking, not a
  measurement" class (`UX-129`, `UX-275`), a `false` that means "not
  measured" rather than "no", a non-zero that weakens every figure
  beside it. A warning belongs where the number is, because a reader
  who skips the door must still meet it.

The test for which one you have: a description answers *what is this?*
and a caveat answers *what may I not conclude from it?* A value with a
declared exception carries **no** `?` — a door beside a sentence
already on screen is the duplication this rule removes.

Measured after: 11% and 9% of the two pages' words, 12 and 18 inline
sentences of 86 and 146 described values.

## 4b. A label is for the reader; the suffix is for the contract

`UX-341` gave every payload key a unit suffix — `_us`, `_bytes`,
`_share` — so the contract says what a number is without a renderer's
help. That is a rule about the **payload**. The label a reader sees is
derived from it, and derivation includes dropping what the value
already says:

```text
wrong    Execution on chain us    43.2 s
right    Execution on chain       43.2 s
```

The suffix is dropped only where the declared quantity accounts for it,
read from the schema rather than from a list of suffixes — a key ending
`_us` that is not a duration keeps its suffix and looks as wrong as it
is (`UX-351`).

## 3d. Table tools scale with the table (round 52)

Measured in round 52: 26 of `macro_micro`'s 38 tables are twelve rows
or shorter and carry a threshold filter per column anyway — most of the
page's 120 inputs — and one of them sits under a boolean column with
the placeholder `> 10`.

- **Filters appear at the row cap**, not below it. Under it the reader
  scans; a filter is a control with nothing to do.
- **A column with one distinct value is a sentence above the table**,
  not a column. "All eleven are `cmake`, none is a leaf" costs one
  line; the column costs eleven repetitions and a sixth of the width.
- **A filter's placeholder is derived from the column's declared
  quantity.** `> 10` under a boolean is the tell that a default was
  chosen where a declaration was available.

Sorting is exempt from all of this: it costs no ink and helps at every
length.

## 2c. The shape channel is a promise, and promises are enforced

§2 specifies sparklines and density strips at length, including a strip
beside every table longer than the row cap. Round 52 counted what the
page actually draws: **one sparkline, zero strips, three SVG elements
in twenty screens**, and the element table §2 names by name carries no
strip.

A written-and-unbuilt section of this document is worse than an absent
one — it lets a reviewer believe the channel exists. So §2 joins §7's
enforcement: **every published distribution renders its strip**,
asserted against the payload rather than a list, and coincident marks
merge into one label rather than overlapping (`19.1 s (p95, max)`, not
`19.1 s19.1 s` printed over `max`). See `UX-350`.

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
