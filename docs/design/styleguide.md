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
| scalar array + `bga:command` | **one monospace command line + copy** | `UX-429`; the same measured shape as the row above, and only the schema knows which it is — a joined-by-comma argv does not run |
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

Nineteen hints, and this table is the one place they are all written
down (`UX-306`). Each names what a schema *declares* about a value;
§1 above is what the page does with it — except the last row, which
declares something about the *contract* and is read by a consumer
rather than by the page. A hint the schemas emit and
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
| `bga:decomposition` | that a section's numbers are a published total split into published parts, each named by its path | the decomposition bar and its sentence (§2d) |
| `bga:interval` | that a set of published values compare on one axis, each named by its path | the interval and its sentence (§2d) |
| `bga:keyed_by` | what a map's own **keys** are, where they are not names — `task_uid` today | the row's label (the element) and its `data-key` (the composite), `UX-391` |
| `bga:explained_by` | the payload key holding this map's **per-key advice for this run** — computed, so not a `description` | the advice on the row of the key it explains, and no second section over the same names, `UX-390` |
| `bga:readers` | which of `findings.READERS` a section serves, by their `R1`-`R5` ids — silent means no role, which is a map that is incomplete rather than a section that serves nobody (`UX-643`) | the reader picker, which promotes and expands a served section and folds the rest |
| `bga:command` | that a scalar array is one command line rather than a list of values — the shell it is spelled for | `classify`, which returns §1's command control for it (`UX-429`) |
| `bga:always_written` | that a key is **not** `required` and yet written on every document — the third state `UX-629` needed, because entering `required` under a live id breaks documents already written | a consumer asking *may be here* or *is always here*; the emitter guarantee is held by `test_a_required_set_grew_under_an_unchanged_id.py`, not by the page |

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

- **Row cap by default.** A table renders its first N rows with
  "N of 1,202 — show all" — the page never silently renders four
  thousand rows again, and never silently hides any either. The
  threshold a table has to pass to open bounded is
  `TABLE_OPENS_BOUNDED_ABOVE` in `bga/viewer/structured.js` and the
  bound it opens at is `openingBound` in `bga/viewer/tables.js`; both
  carry the argument for their value, and this sentence does not
  restate it. The strip (§2) is what makes the cap honest: the shape
  of the whole is visible before the fold.
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

## 1b. Every published field reaches a reader, or the page names the ones that do not (round 55)

`UX-338` gave the page `DRAWN_ELSEWHERE`: a population the page
deliberately does not draw on its own, together with a sentence saying
where it went instead. `element_join`'s entry says

> merged into the one element table (`elements`)

Round 55 measured that merge field by field. Of `element_join`'s **28
published fields, 13 reach no rendered node** — among them twenty-three
recommendation sentences the analyzer wrote for exactly this reader:

```text
holds 44% of the critical path and fixing it is worth 12.1s (26.1% of
the build), but runs at only 0.90 cores busy - it is waiting, not
computing, and its native build asked for -j1: remove `notparallel` /
raise its job count before touching its sources
```

`severity` is drawn for all twenty-three. `text` is drawn for none: the
sentence exists only inside `<script type="application/json"
id="bga-report">`. So three clauses, all of them about the same
distinction between a *promise* and a *projection*:

- **"Drawn elsewhere" means every field arrives elsewhere.** A merge
  that keeps four of twenty-eight columns is a projection, and a
  projection says what it dropped, in the sentence, where the next
  reviewer reads it.
- **A published sentence outranks a published number.** Where the
  payload carries prose written for this reader, the page prints the
  prose. A severity chip beside a withheld sentence is that ordering
  inverted.
- **The embedded payload is not a reader.** `#bga-report` exists so the
  export can boot from `file://`. A value that reaches only it has
  reached nobody, and a coverage instrument that reads the file rather
  than the DOM will say it arrived.

The same measurement over `provenance` — `UX-229`'s "why bga believes
what it believes" — found the claim drawn and the rule withheld:
`rule.module` 0 of 12, `rule.name` 0 of 5, `rule.observed_path` 0 of 5,
`rule.sentence` 1 of 12, `unpublished_inputs` 0 of 3. A provenance
section that shows the conclusion and not the rule is the one section
on the page whose whole job it fails.

## 2d. A drawing per question; the vocabulary grows when a question needs a shape (round 55)

`UX-350` built §2 and the census moved: 1 sparkline and 0 strips became
1 sparkline and 5 strips on `golden`, 15 on `macro_micro`. The channel
exists. What it does not yet have is *range*: the page's whole visual
vocabulary is **two shapes**, the density strip and one sparkline, and
19 of `golden`'s 43 sections and 29 of `macro_micro`'s 58 carry six or
more numbers with nothing drawn at all.

The rule is not "draw more". It is:

- **A drawing answers a question, not a table.** The test is whether a
  reader can state the question the shape answers before reading the
  caption. `producer`'s 74 numbers are provenance and want no drawing;
  `floors`' 11 are the tool's central claim — *how much of this build
  is irreducible* — and want one badly.
- **The vocabulary grows only where an existing shape cannot make the
  comparison.** A strip shows a distribution; a sparkline shows an
  ordered series. Neither shows a *decomposition* (wall-clock split
  into chain, waiting and slack) or an *interval* (a confidence range
  against a threshold). Those are the two shapes the payload is asking
  for, and they are the only two this round proposes.
- **A shape that is added is added to §1's table**, with the published
  shape that selects it, so a schema addition of that shape draws with
  no viewer edit — `UX-193`'s property, applied to drawings.

## 3e. Volume is a budget, not only distance (round 55)

`UX-347` bought the distance budget with chapters that fold, and it
worked: the page a reader lands on went from 11,286 px to 3,548
(`golden`) and 18,148 to 5,588 (`macro_micro`), −69%. Opened, the same
two pages are **13,844 px and 24,689** — 23% and 36% *larger* than the
pages the distance complaint was filed against.

Folding moved the cost; it did not remove it, and nothing measured the
part that moved. So the distance budget gains a sibling:

- **Landed distance and total volume are two budgets and both are
  bound.** Words, controls and height, measured with every chapter
  open, on the page an export actually produces.
- **A fold is not a licence.** "It is behind a chapter" answers the
  distance budget and says nothing about the volume one.
- **The bound is set against a measured page and moves only with a
  filed reason** — the discipline §3c already uses for distance.

Measured on the finished page at 1440x900, and the bounds set from it
with roughly a fifth of headroom on the largest run in each class.
Round 59 (`UX-367`) added the third row and split the bounds by size;
the readings below are round 66's, taken after `UX-419`, with the words
column re-read in round 73:

```text
                 elements   landed   opened    words   controls    nodes
golden                  4    3,800   15,618    7,144        427    2,498
macro_micro            11    5,965   31,804   12,002        750    5,686
budget, to 50 elts             7,100   35,000   12,600        800    7,900

scale               1,202    4,763   26,242   36,542      1,941   24,294
budget, to 4,000 elts          7,000   32,000   41,000      2,300   27,500
```

`UX-681` moved the small class's two height bounds, and only that
class: `macro_micro` measures 7,018 landed and 34,678 opened once
fan-in ships. The 18 px is the element table's new "Dependencies read"
column wrapping one header row; the 678 is the `fan_in` columns, the
`fan_in_distribution` strip beside the blast one it mirrors, and two
findings. The class above is untouched at 7,000 / 32,000, which is what
says the page still gets *denser* with scale rather than the budget
being loosened for everyone.

`UX-526` measured the large class at its **top** — the same seeded
generator at `--layers 20 --width 200`, 4,002 elements — and every one
of the four opened bounds was past: 107,352 words, 4,774 controls and
73,075 DOM elements against 41,000 / 2,300 / 27,500. A class asserted
only at its bottom is `UX-367`'s own defect one size up. The rows and
pairs a bound does not show now leave the document instead of staying
in it hidden, and the class is bounded at both ends:

```text
                 elements   landed   opened    words   controls    nodes
scale               1,202    5,007   26,584    8,259        787    4,732
xl                  4,002    4,937   27,230    8,275        812    4,960
budget, to 4,100 elts          7,000   32,000    9,000        900    5,500
```

Height does not move at all — a bounded row costs no pixels, which is
`UX-419`'s finding — and the other three fall by an order of magnitude,
because at 4,002 elements 96,065 of the page's 107,352 words were the
hidden half of one `dl`. The nodes bound came down again one item
later: `UX-527` replaced the Perfetto picker's one-`<option>`-per-element
`<select>` with a search box drawing eight, 4,119 DOM elements to 126,
and `test_the_budgets_are_not_slack` is what asked for the restatement.

The small class's words bound moved 12,000 -> 12,600 in round 73, and
only that one:

```text
                golden   macro_micro
before round     6,882        11,616
after UX-479     7,121        11,979   (+239, +363)
after UX-475     7,144        12,002   (+23,  +23)
```

`UX-479` added a finding the recipe-author had no answer without, and
a finding is not one sentence — it is the sentence, its provenance
record, its row in the reader's block and its copy text, which is why
one claim is 363 words on an eleven-element page. `UX-475` made the
graph-shape sentence carry the count that tells a mesh from a chain,
and replaced a claim rather than adding one, which is why it is 23.
Height, controls and nodes did not move at all — two sentences are not
a table. The trimming that came first, and what is left of the
headroom, are in the note above `BUDGETS`.

**`nodes` is the fifth column because the other four are blind to a
table.** `UX-366` lifted the element table's cap, putting 1,177 more
rows in the DOM: height did not move (a hidden row occupies none),
controls moved by three, and *words* moved by 1,167 — because the cells
carry no whitespace between them, so `textContent` renders a whole
six-column row as `layer00/mod023.bst9.0 s645falsecmakefalse`, one
"word". The DOM element count is the measure that saw it, 12,305 →
22,977. A budget that cannot see the page's largest population double
is not measuring volume.

**Landed height is one number for every class**, and that is the
result rather than a shortcut: at 1,202 elements the page a reader
lands on is 4,763 px — *shorter* than the 11-element fixture's 5,965.
`UX-347`'s fold scales.

The opened budgets were stated per class because they did not, and
`UX-419` is why they now nearly do. A map (`dl`) had no bound at all,
so at 1,202 elements every one of them drew every pair and the opened
page was 55,998 px; bounded, it is 26,242 — *below* the 11-element
page's 31,804. The large class's opened bound came down 66,000 →
32,000 with that as its reason, and the two rows are kept apart anyway:
`words` and `nodes` still grow with the run by 3.3x and 4.3x, which is
the growth the split was for.

Words and controls are one number rather than two, and that is a fact
about the mechanism rather than a simplification: the chapters hide
their sections with CSS, so every word and every control is in the
document from the first byte. Folding changed how far a reader scrolls
past them and nothing else — which is precisely the cost this budget
exists to keep visible.

`tests/unit/test_the_page_has_a_volume_budget.py` asserts both budgets
in **one** guard, so a change trading one for the other has to say so.
It also holds the bounds to being reachable: the largest run in each
class must sit within a factor of two of every one of them, because a
bound nothing can reach is not a bound. That clause is what forces a
budget *down* when a later item makes the page smaller — `UX-366` is
the next one due to.

## 4c. A control acts on the scope its label names, and it acknowledges the press (round 55)

Every control class on the page was pressed, on the page a user gets,
in the state a user lands in. Twelve classes; two of them do not keep
the promise their label makes.

**"Expand all" expanded nothing.** The pair was built on
`collapsible().all()`, which walks *sections*. `UX-347` moved the fold
to the *chapter*. Sections are default-open, so from a fresh load
`all(false)` set open what was already open:

```text
                          height   chapters open   sections data-collapsed=true
landed                    3,548              1/7                             0
after "Expand all"        3,548              1/7                             0
after opening each
  chapter by hand        13,844              7/7                             0
```

"Collapse all" worked, because sections were the layer it shut — so the
pair was not symmetric: one half acted on the fold the reader sees and
the other on a fold that is already open. A reader who wanted the whole
document clicked six chapter headings. `UX-355` gave `collapsible` an
`enclosing` layer, injected rather than imported, so both halves drive
both folds and "Expand all" now reaches 13,844 px in one press.

**"Copy 11 rows" said nothing.** Of four copy controls, `copy-step`,
`copy-sql` and `copy-view` change their own label on success; the most
numerous one — 13 of them on `golden`, 23 on `macro_micro` — wrote to
the clipboard and left no trace on the page at all. It now restores its
label through the function that builds it rather than a string captured
at build time, because the count that label carries follows the filter
and the bound.

- **A control's label names its scope, and the scope is the layer the
  reader is looking at.** When a fold moves to a new layer, every
  control that names "all" moves with it.
- **Every action is acknowledged where the finger is.** A clipboard
  write is invisible by construction, so the control says so itself.
  `UX-279` made every copy control say *what* it copies; this makes it
  say *that it did*.
- **A control is exercised in the state a reader meets it in.**
  `UX-194` forbade dead controls and was satisfied by a listener being
  attached. A listener that runs and changes nothing is the same defect
  with a passing guard.

## 6a. What this borrows from Apple, and what each borrowing costs (round 55)

The user's standing reference for "considered". Five rules taken from
Apple's human-interface tradition, each with the measurement that says
what it would cost here, and one the page already gets right.

| borrowed rule | measured here | what it costs |
|---|---|---|
| **Deference** — chrome recedes so content leads | the `?` door is 121 of `golden`'s 257 buttons (47%) and 175 of 381 (46%) | one door per *block* instead of per value; §4a already moved the sentence, this bounds the door |
| **Symmetry** — every gesture has an inverse of equal cost | "Collapse all" shuts six sections; "Expand all" is a no-op | §4c |
| **Feedback** — an action reports, at the point of action | 3 of 4 copy controls acknowledge; the most numerous does not | §4c |
| **One primary action per view** | the emphasis budget (§4) bounds *color* per block and nothing bounds *actions* | extend §4's budget from tone to affordance: one emphasised action per block |
| **The default state is a complete answer** | the landed page is 3,548 px, one chapter, and it does answer "what should I do?" — verdict, three ranked elements, a runnable command | nothing; this is the property §3e's volume budget exists to protect |

And the one the page already borrowed well: **progressive disclosure
that discloses**. A chapter heading reads "Where did the time go? **Show
10 sections**" — the fold names its own weight before it is opened,
which is the rule `UX-318`'s depth budget was filed for and the model
the `?` door should be rebuilt on.

Two Apple rules are deliberately **not** borrowed. *Consistency across
an ecosystem* is a rule for a platform vendor and this is one page.
*Delight* — motion, easing, ornament — is refused outright by the
export constraint at the top of this document: a pattern that needs a
server or a hover to mean anything is never the meaning.

## 3f. A budget is measured at the size the page is used at (round 58)

`UX-360` gave the page a volume budget and a guard that holds it. The
guard runs over the two committed fixtures, which are **11-element**
runs. Measured on the seeded 1,202-element run — the size
`gen-synthetic` exists to probe:

```text
                    budget   macro_micro (11)   scale (1,202)
opened height       34,000            28,257          54,968
words               12,000             9,883          33,864
controls               800               660           1,922
```

Every bound is exceeded 1.6-2.8x where no guard looks. So the rule the
budget needs is one level up from the numbers:

**A bound is stated together with the size it was measured at, and it is
enforced at the largest size the tool tells people to use.** A budget
measured only where the page is small has never met the page.

This is `UX-363`'s lesson about the tier budget, in the other document:
there, one measurement was compared against the number that made it look
sized. Here, one *population* is.

`UX-367` is the item, and closing it taught the rule its own second
half. **The filing's own scale figures were measured wrong**: it
reported 70,577 px for the scale page against 28,213 for
`macro_micro`, but the first was measured with every `<details>`
forced open and the second with them closed. One row, two instruments.
Same instrument both ways, the overrun is 1.6x and not 2.1x — real,
and smaller than the number that argued for the item.

So: **a comparison is made with one instrument, and the instrument is
part of the measurement.** A budget stated at the size the page is used
at is worth nothing if the two sizes were not measured the same way,
and a table whose rows disagree about what was opened is the same class
of error as a bound nobody enforces.

## 1c. A superlative is a measurement, not an adjective (round 58)

`UX-326` made the tool's sentences contracts. Round 58 found the
strongest form of that rule being broken by a label:

```text
wait-category   "Biggest Opportunity: 5.9% of wall-clock (2.72s)"
joint-saving    "the top 3 are worth 23.1s (50% of the build)"
```

The finding that carries the word is 8.5x smaller than the one that does
not, and `headline.top_actions` agrees with the second.

**A word that asserts a maximum — biggest, largest, worst, top — is a
claim about every other candidate, and is only written where the tool
has compared them.** Where it has not, the sentence says what it
measured and stops. This is `UX-362`'s rule ("say what you own") applied
to comparatives rather than to planes.

The corollary the same round found: **the order a list is published in
is a claim too.** `findings[0]` and `findings[1]` are `info`, and the
first says of itself that it is "the intent rather than a finding". A
reader who reads top-down spends their first two entries on non-actions,
while the page's own first screen leads correctly. Two surfaces, one
payload, and only one of them ordered.

`UX-365` is the item.

## 4d. A handoff hands over this run's values (round 58)

The query library ships thirteen queries; three carry an `{element}`
placeholder, and the page fills all three with the literal `core.bst` —
a real element **of one fixture**, compiled into a library shipped for
every project.

```javascript
return question.sql.split("{element}").join(question.example ?? "");
```

The page knows this run's elements. It draws them in a table and names
three in `headline.top_actions`. The substitution reads none of them.

**Where the page hands the reader something to run elsewhere — a query,
a command, a link — every value in it comes from this run, or the page
says which value the reader must supply.** A pasted query that returns
zero rows because it names somebody else's element teaches the reader
that the handoff does not work.

`UX-218` already applied this to commands (`bga blast <this element>`);
this is the same rule reaching the SQL.

`UX-369` and `UX-368` are the items.

## 5a. Repetition is spent from the volume budget (round 58)

Counted over rendered blocks — `p`, `li`, `summary`, `td`, `h3`, `h4`,
longer than 40 characters — on `macro_micro` fully opened:

```text
138 distinct blocks, 17 repeated
repeated text: 4,742 of 21,914 block characters = 21.6%
x9  "No named threshold; computed in bga/findings.py"
x7  "Where the time is: 4 element(s) are 71.9% of the 43.2s critical path…"
```

Every repeat is individually defensible — `UX-229` says a claim carries
its provenance. **The total is nobody's, which is how it reached a
fifth of the page.** Three of the repeats are visible on the first
screen at once, because the decision chapter draws three top actions and
each carries the same provenance sentence.

The measurement rule matters as much as the bound: **count what a reader
sees as a unit.** Splitting `textContent` into sentences found *zero*
duplicates on the same page, because the repeated blocks sit inside
different surrounding text.

`UX-371` is the item.

Round 59 set the bound. Measured over every `p`, `li`, `summary`,
`td`, `h3`, `h4` longer than 40 characters, with every chapter and
every `details` open, after this item's own reduction:

```text
                     blocks  distinct  repeated chars  of total  share
golden      before       81        61           1,876    11,048  17.0%
            after        77        61           1,434     9,730  14.7%
macro_micro before      180       138           4,769    26,919  17.7%
            after       176       138           4,401    25,681  17.1%
budget                                                           21%
```

Both readings come from one instrument. Round 58's 21.6% above was
taken over a different block population and is not comparable with
either column — the repeated character count agrees to within 27 B,
the denominator does not.

**The reduction, and why it was the right one.** Every repeat is
individually defensible — a claim cited twice is cited twice — so the
question is where a repeat is *not* a citation. The decision chapter
drew three top actions and rendered the ranking rule under each: three
copies of one record, on the first screen, saying nothing about the
row they sat under. The rule is a property of the ranking, so it is
stated once below the list it ranked — the reader came for the actions
— and each fold says what differs. Where the actions come from
different findings the rule is not shared and the per-row placement
stands, so this is a branch and not a move.

The budget has a second half, and it is the one that makes it mean
anything: **the count of distinct blocks may not fall**. The cheapest
way to drive a repetition ratio down is to say less, and losing a
claim is not deduplicating it.

## 6b. What this page may depend on (round 65)

The standing question `UX-397` filed — *has this page reached the point
of needing a table library?* — is answered here as a **rule**, because
the next candidate will arrive with the same argument and deserves the
same arithmetic rather than the same debate.

**A JS dependency is admitted only when both hold:**

1. the behaviour **cannot** be met by the table factory plus a platform
   primitive inside the volume budget (§3e), shown by a measured
   before/after of the export's *page* half — the `UX-382` split, not
   the total; and
2. the library's wiring-plus-conformance cost **measurably undercuts**
   the in-house cost, counting the work of making its DOM pass §1's
   mapping, §2a's grades and §7's walks.

The named prior is `tools/native_trace/trackevent.py`: a protobuf
writer written here rather than a protobuf dependency taken, for
exactly these two reasons.

**Why condition 1 is harder to meet than it looks.** The argument for a
library is normally *this behaviour would otherwise be re-implemented
in every module*. Measured, that premise is false here:

Round 65, when this was written:

```text
$ grep -ln 'renderTable\|buildTable' bga/viewer/*.js
bga/viewer/app.js          the one caller outside the factory
bga/viewer/primitives.js   the factory's parts
bga/viewer/structured.js   the factory

$ grep -rn 'el("table"' bga/viewer/*.js
bga/viewer/structured.js:435    one <table> is constructed in the viewer
```

The two counts are derived rather than restated (`UX-582`): the
paragraph below had aged by one module before anything read it.
`test_the_styleguide_names_its_guards.py` re-runs both:

```text
$ git ls-files -- 'bga/viewer/*.js' | wc -l
22                                  viewer modules
$ git grep -l 'el("table"' -- 'bga/viewer/*.js' | wc -l
1                                   modules that construct a table
```

Every table on the page — 31 of them on the round-63 export — is built
by `buildTable`/`renderTable` in `structured.js`, which already owns the
declared column specs, declared-not-sampled sorting (§3, `UX-284`), the
preset menus (`presetColumns`), Top-N and fold-the-middle, the density
strip, the copy control and `interrogable`'s filter bar. Every other
module *consumes* the factory; none hands one. So a behaviour
wanted on all 31 tables is **one change to one function**, and every
future table inherits it — which is the economics a library is adopted
for, already owned.

**And what condition 2 has to beat.** For the concrete candidate
(Tabulator, ~400 KB) on the export this rule was written against:

```text
bga view tests/fixtures/macro_micro/run --export
  export total   417,859 B
    page half    269,531 B
    data half    148,328 B
```

A 400 KB dependency is 1.5x the entire page half. Beyond the bytes it
imports three costs the filing did not price: **the styleguide is law
over this DOM**, so a library's markup either fails §1/§2a/§7's walks or
gets wrapped until the visual contract is re-implemented on top of it;
**the console guard** (`UX-334`) holds every served page to zero CSP
violations, and table libraries write inline style attributes as a
matter of course; and **there is no toolchain to carry it** — no npm, no
bundler, no lockfile — so one runtime dependency imports the whole
supply-chain and upgrade question `UX-296` was decided to avoid.

The rule prices candidates; it does not blacklist them. What it forbids
is adopting one on an impression.

## 6c. The browser is the library (round 65)

§6b says a dependency is admitted only when the factory *plus a
platform primitive* cannot do the job. This is the list of primitives,
so "can the platform do it" is a question with an answer rather than a
shrug. It is the living copy: a widget that wants a library checks here
first.

| primitive | what it replaces | state here |
|---|---|---|
| `content-visibility: auto` + `contain-intrinsic-size` | virtual scrolling — offscreen sections stop costing layout | **used** (`style.css`, sections inside a chapter) |
| `IntersectionObserver` | a scroll handler that reads layout every frame; scrollspy | **used** (`nav.js scrollspy`) |
| `scroll-margin-top` | anchors landing behind sticky chrome | **used** since `UX-317` |
| `popover` / `<dialog>` | overlay plumbing for the `?` apparatus and table focus | not used — §2b's mechanism is hand-rolled and works; a rewrite needs its own filing |
| `@container` | resize listeners for density adaptation | not used — §2a's grades are viewport-wide today |
| `:target` | selecting the jumped-to section without JS | not used |

**What `content-visibility: auto` bought, measured.** The page fully
expanded — every chapter open, every fold open, which is the state a
reader who opens the report is in — with the optimisation forced off
and on in the same browser, median of 25 forced reflows:

```text
fixture       DOM nodes    off                     on
scale (1,202)    23,040    70,932 px  25.9 ms      41,669 px   2.2 ms
macro_micro       5,366    48,224 px  12.9 ms      42,777 px   2.3 ms
golden            2,441    23,863 px   6.4 ms      27,214 px   1.9 ms
```

The number that matters is not the ratio at any one size — it is that
**layout cost stops tracking the document**. Off, it is 6.4 → 25.9 ms
as the run grows from 2,441 to 23,040 nodes; on, it is ~2 ms at every
size, because the browser lays out the viewport rather than the report.
That is the property `UX-397` was going to buy with 400 KB.

**And what it costs, also measured.** `scrollHeight` becomes an
estimate until a section has been rendered once: −41% at scale, +14% on
`golden`, from the 600px placeholder being smaller than a scale
section and larger than a golden one. `auto` in `contain-intrinsic-size`
is what makes it converge — a section keeps its real size once seen —
but a reader dragging the scrollbar before scrolling gets an estimate.
The page's own volume guards therefore force the optimisation **off**
before measuring: volume is a question about content, not about paint.
Turning it off there would hide its removal, so
`test_the_browser_is_the_library.py` holds the other half — the shipped
stylesheet really does carry it.

**Where the mark goes.** The rail's "you are here" is weight plus a
marker, never a tone: §4's emphasis budget is spent on findings, and
orientation is not severity. `aria-current="location"` carries the same
fact to a screen reader.

## 6d. Every control has a resting appearance (round 70)

`style.css` had **no base `button` rule**. Controls were styled where a
section happened to need one and everything else got the browser's
default. Counted over the booted export at 1440x900:

| | before | after |
|---|---|---|
| buttons (`macro_micro`) | 429 | 429 |
| distinct computed looks | 11 | 3 |
| on the UA's beveled grey | 52 | 0 |
| distinct looks at 1,202 elements | — | 4 |

`2px outset` on `rgb(239,239,239)` is the 1995 UA button, inside a page
that otherwise runs on a declared token palette. That is not a matter of
taste: it is a control no rule in this repository has ever described.

**The four grades**, keyed on the part of the appearance that carries
them — background, border style, radius. A control is one of these or
it is a defect, and
`tests/unit/test_every_control_has_a_resting_appearance.py` reads them
out of a real browser rather than out of this file.

| grade | look | what it is for |
|---|---|---|
| **standing** | `--muted-bg`, solid, 3px | a control you press on purpose — copy, investigate, the rail's steps |
| **quiet** | transparent, solid, 3px | an inline toggle beside something it must not compete with — a fold, a chapter, a JSON door |
| **reveal** | transparent, **dashed**, 3px | shows more of what is already here rather than acting: `fold-more`, `path-more` |
| **door** | transparent, solid, **50%** | `UX-317`'s circular `?` |

`UX-436` asked for three. There are four, because **reveal** is a real
distinction with exactly two members that now match each other, and
deleting it to reach a number would be the number driving the design.

Two things this section does **not** do. It spends nothing on motion or
ornament: §6a refuses those on the export constraint and that refusal
stands — zero transitions, zero shadows, both asserted. And it is not
§4's emphasis budget, which bounds *tone* per block and says nothing
about whether a control has a resting appearance at all; a button can be
entirely un-emphasised and still not be the browser's.

## 2e. A ranked map is a table's question, not a fifth shape (round 65)

§2d says the vocabulary grows *only where an existing shape cannot make
the comparison*. `UX-411` is the first time that rule was applied to
refuse one, and the refusal is worth writing down beside the rule.

`UX-396`'s census found two sections publishing a **ranked map** — one
measure over many data keys, with no order the schema declares:

```text
by_binary            11 values, all count          one call count per binary
wall_clock_share_us  11 values, all duration_us    one duration per task uid
```

None of the four instruments draws it. A series is ordered, a
distribution is a percentile record, a decomposition is a published
total in published parts, an interval is a value on an axis. So the
question §2d asks is whether the comparison can be made without a new
shape, and it can:

- **The page already answers "which is biggest", and not with a
  drawing.** Sort a column, choose `Top N by <column>`, type in the
  filter box, read `columnStrip` beside the header (§3d, §2a). That
  mechanism is general and every table has it. §4's emphasis budget
  spends emphasis once per block; a fifth instrument would be a second
  answer to a question already answered.
- **A ranked map grows with the payload, not with the run** — one key
  per binary, per task uid. A bar per key is unbounded by
  construction, which is what §3e's volume budget exists to stop.
- **`UX-193`: the page chooses nothing.** Drawing a ranking asserts an
  order the schema does not declare.

The decision is recorded where the census reads it, in
`tests/unit/test_a_shapeable_population_is_drawn.py`'s `RANKED_MAP`,
and `test_the_four_instruments_are_the_four_that_exist` is its guard: a
fifth name appearing there means this reasoning was revisited.

**This is a refusal of a drawing, not of the bound.** Measured at 120
keys, both sections draw every pair and no table — `UX-413`'s defect in
the shape its sweep cannot see, filed as `UX-419`.

## 1d. A command is a shape, and the shape is one line (round 69)

The page's "What should I run next?" control is a table whose middle
column is headed `Run`. Probed in the booted export of a 1,202-element
run, at 1440x900:

```text
mono=False code=False btn=False  bga, blast, layer08/mod073.bst, /tmp/…
```

not monospace, no `code` element, no copy control. Behind it:

```json
"argv": ["bga", "blast", "layer08/mod073.bst", "/tmp/…/run"]
```

**The same field renders correctly two other places.** `decision.js:737`
and `views.js:500` both do `argv.join(" ")` and attach a copy control.
The third site declares it a table column (`bga/schemas.py:3134`) and
gets the generic array path.

The generic path is not misbehaving. `["bga", "blast", …]` is a *short
scalar array*, and §1 says a short scalar array renders as the inline
`code` list — values, separated by commas. **The mapping is being
followed. The mapping has no row for a command.**

So the rule is one level up from the bug:

**A value the reader is meant to paste into a shell is one string, not
a list of its words.** It renders as a single line, monospace, with the
copy affordance §4c requires, and its separator is the shell's — never
the comma a list-rendering control supplies. A command is a *shape*, so
it lands in §1's table with a hint that declares it, rather than each
site joining the array itself and one site forgetting.

This is `§4d`'s failure wearing different clothes. There, a query was
handed over filled with somebody else's element; here, a command is
handed over punctuated so it cannot run. Both look complete. Neither
works when pasted, which is the only test either one has.

The general form, and the reason this sits in §1 rather than in a
bug report: **where one payload field is rendered by more than one
site, the shape is what they must agree on.** Two sites knowing a
private fact about a field — that its elements join with a space — is
the drift the shape-dispatch exists to prevent, and the third site is
not the defect so much as the proof.

`UX-429` is the item. Its row in §1's table and its hint in §1a land
together with the schema change, because
`tests/unit/test_the_contract_names_its_vocabulary.py` holds §1a and
`bga/schemas.py` equal in both directions: a documented hint nothing
emits reddens exactly as an undocumented one does.

## 3g. A budget counts what its consumer spends (round 69)

`tools/bga_view.py` carried **one** bound on the Perfetto handoff when
this section was written:

```python
TRACE_BUDGET_B = 4 * 1024 * 1024
```

Measured on a 1,202-element run with both planes, 14,424 traced
processes:

```text
                      measured        bound
trace bytes            795,371    4,194,304    19.0% of it
slices                  14,446            -
tracks                  15,650            -    nothing bounds this
```

The trace sits at a fifth of its byte budget and carries **more tracks
than slices** — one process track per element, one thread track per
traced pid. Perfetto draws a row per track, so the reported freeze is a
drawing cost. Bytes are what the budget counts; tracks are what the
consumer spends.

**A budget is stated in the unit its consumer actually spends, and a
bound on a proxy for that unit is not a bound.** §3f gave the budget
family its first half — a bound is enforced at the largest size the
tool tells people to use. This is the second: measured in the right
currency. A capture can pass this budget with room to spare and be
unopenable.

What makes this one hard to see, and worth a section rather than a
fix: **the byte figure is not wrong.** It is real, cheap to obtain,
honestly reported, and it correctly bounds the thing it was written
for — transfer, and whether the export inlines. It simply is not a
measurement of what the reader is complaining about. That is the
fixing guide's §5 arriving on the design side, where the tell is not a
bad number but a good number answering an unasked question.

**Closed, and where.** `UX-430` added `TRACE_TRACK_BUDGET`, the bound
in the unit above; `UX-446` put all three in
[`cli.md`](../guides/cli.md)'s ceilings table and derived that table
from `bga_view.CEILINGS`, so a fourth bound in a fourth unit reddens a
guard rather than waiting for a reader to be stuck. What is still open
is the bound's *value*: `UX-445` measured the emitter's curve, could
not reach Perfetto's UI to measure the drawing cost, and left the
number where it was rather than re-siting it on the wrong evidence -
which is this section's own rule, applied to its own fix.

The test to apply to any bound on this page: *name the thing that goes
wrong when it is exceeded, then check the budget counts that thing.*
Here the thing that goes wrong is Perfetto not drawing, and nothing in
the budget's units appears in that sentence.

`UX-430` is the item.

**And a page has modes, not only sizes.** `#actions-group`, the Perfetto
handoff in the rail, measured on the same capture in both:

```text
                 group      share of rail    visible paragraphs
export           208x39px          4.9%              1 of 3
served          208x157px         19.5%              2 of 3
```

Four times the height in the mode `bga view` opens by default — the
export hides two of the three paragraphs, so a guard whose fixture is
the export reports a box the reader never has. Its fixture says the
choice out loud, and reasonably: "the header, its budget and the room
rule are identical in both". They are. The handoff group is not, and it
is the thing being measured.

So §3f's rule has a second dimension. **A bound is enforced at the
largest size the tool tells people to use, and in the mode people use
it in.** `UX-435` is the item.

## 4e. A handoff says what it could not carry (round 69)

Same capture. `run/graph.json` holds 3,500 dependency edges; the
emitter reported:

```json
{"flows": 19, "flows_dropped": 0}
```

3,481 edges reached no arrow, and the counter that exists to report
loss read zero. `_plane1_flows` has two skip paths and counts one — the
uncounted one means "one end of this edge produced no task", which is
what a cached element is, and therefore what most edges of an
incremental build are.

**A handoff that drops part of what it was given states how much and
why, and a counter that names one reason for loss reports every
reason.** §4d says a handoff hands over this run's values; this is its
converse — where it cannot, it says so rather than handing over a
smaller thing silently.

The sharp edge is the zero. A zero meaning "nothing was lost" and a
zero meaning "this counter does not watch that door" are
indistinguishable to the reader, and the second is strictly worse than
no counter at all: **it converts an absence the reader might have
questioned into an assurance.** A reader who sees 19 arrows and no
count wonders. A reader who sees 19 arrows and `dropped: 0` concludes
the graph really is that sparse, and stops.

So the rule has a second clause: **a count of what went wrong is
reported to the reader, not only to the caller.** `flows_dropped` rides
the render result and is asserted in a guard; `describe()` never prints
it and nothing under `bga/viewer/` reads it. A number that only a test
can see is not a report.

`UX-431` is the item.

**Closed in round 70.** `flows_dropped` is now `flow_losses` - the edge
count, how many became arrows, and one key per named reason for the
rest, with the invariant that they sum. `describe()` prints it on every
run that had edges, including the run that drew them all, and
`questions.js` renders the same sentence on the handoff page. The
served page is the half still missing (`UX-443`): `UX-296` moved the
render off the startup path on purpose, so `run.json` is written before
anything has counted an edge.

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

**The ledger below is derived** (`UX-582`).
`tests/unit/test_the_styleguide_names_its_guards.py` reads every
`§N` mention in the files `git ls-files -- 'tests/unit/*.py'` names and
holds this table to them **both ways**: a row naming a guard that does
not cite that section reddens, and a guard citing a section this table
omits reddens. A section with no guard is a row with an empty guard
cell and a reason — which is the state round 55's five were in when
they were written, made visible instead of narrated in a paragraph
that then aged. Before it, §7 said seven sections had no guard and
four of them had one.

**The ids a scan cannot attribute.** `§1`–`§7`, `§4a` and `§6a` are
also headings in [`fixing-guide.md`](../contributing/fixing-guide.md),
and a bare `§5` belongs to whichever document its sentence is about.
Those rows say `named` — held to existing and citing, not to being
the whole set, and a row saying it for an id the scan *can* attribute
is red. The exclusion is read off the fixing guide's own
headings, so a renumber there moves it.

| § | guard | note |
|---|---|---|
| §1 | `test_the_mapping_is_law.py` | named |
| §1a | `test_a_command_renders_as_a_command.py`, `test_the_contract_names_its_vocabulary.py`, `test_the_vocabulary_has_the_shape.py` | |
| §1b | `test_the_merge_carries_every_field.py` | |
| §1c | `test_the_first_finding_is_an_action.py` | |
| §1d | | `UX-429`'s `test_a_command_renders_as_a_command.py` holds it and cites §1 and §1a, not §1d |
| §2 | `test_the_shape_before_the_rows.py`, `test_the_shape_channel_is_built.py` | named |
| §2a | `test_a_drawing_is_graded.py`, `test_emphasis_is_a_budget.py`, `test_the_page_conforms_to_its_sections.py`, `test_the_report_you_can_attach.py`, `test_the_views_that_draw.py`, `test_the_vocabulary_has_the_shape.py` | |
| §2b | `test_a_drawing_is_graded.py`, `test_apparatus_in_its_place.py`, `test_the_page_conforms_to_its_sections.py`, `test_the_report_is_read_not_decoded.py`, `test_the_report_you_can_attach.py` | |
| §2c | | `UX-350`'s `test_the_shape_channel_is_built.py` built the channel and cites §2 |
| §2d | `test_the_vocabulary_has_the_shape.py` | |
| §2e | | no guard cites it |
| §3 | `test_the_tools_scale_with_the_table.py`, `test_one_click_from_investigation.py` | named |
| §3a | `test_a_level_names_who_is_in_it.py`, `test_a_value_shows_what_it_is.py`, `test_the_chain_folds_and_clicks_are_counted.py`, `test_the_fold_says_how_deep_it_goes.py`, `test_the_merge_carries_every_field.py`, `test_the_page_conforms_to_its_sections.py`, `test_the_provenance_names_its_rule.py`, `test_the_report_you_can_attach.py`, `test_the_store_section_takes_a_window.py`, `test_why_bga_believes_what_it_believes.py` | |
| §3b | `test_the_chain_folds_and_clicks_are_counted.py`, `test_the_page_conforms_to_its_sections.py` | |
| §3c | | no guard cites it; §3e's volume budget is the measured half |
| §3d | | `UX-349`'s `test_the_tools_scale_with_the_table.py` holds it and cites §3 |
| §3e | `test_the_page_has_a_volume_budget.py` | |
| §3f | `test_the_handoff_box_is_measured_served.py` | |
| §3g | `test_the_ceilings_reach_a_reader.py` | |
| §4 | `test_emphasis_is_a_budget.py`, `test_the_palette_is_validated.py`, `test_a_drawing_is_graded.py`, `test_apparatus_in_its_place.py`, `test_the_browser_is_the_library.py` | named |
| §4a | | named; `UX-346`'s `test_a_sentence_lives_on_its_door.py` holds it and cites no section |
| §4b | | `UX-351`'s `test_the_label_is_for_the_reader.py` holds it and cites no section |
| §4c | `test_a_command_renders_as_a_command.py`, `test_a_control_acts_on_what_it_names.py` | |
| §4d | | no guard cites it; `UX-368` and `UX-369` are the filed items |
| §4e | `test_the_ceilings_reach_a_reader.py`, `test_the_served_handoff_counts_its_edges.py` | |
| §5 | | named; `test_the_palette_is_validated.py`, named in §5's own prose, cites §4.3 and §4.5 only |
| §5a | | no guard cites it; the easy one passes forever, below |
| §6 | | named; `test_the_numbers_have_a_sentence.py` and `test_the_shape_before_the_rows.py` hold the sentence and the `n`; neither cites §6 |
| §6a | `test_every_control_has_a_resting_appearance.py` | named; §6a's refusal, not a fifth copy of four rules |
| §6b | `test_one_factory_builds_every_table.py`, `test_the_handoff_rides_the_rail.py` | |
| §6c | `test_the_browser_is_the_library.py`, `test_the_report_you_can_attach.py` | |
| §6d | `test_every_control_has_a_resting_appearance.py` | |
| §7 | `test_emphasis_is_a_budget.py`, `test_the_styleguide_names_its_guards.py` | named |

What the rows with no guard were written from, rounds 58 and 69, kept
because a section written from a measurement is only re-arguable with it:

```text
§1c   "Biggest" on 2.72s against a sibling worth 23.1s          UX-365
§1d   `bga, blast, layer08/…` in the `Run` column, against
      `argv.join(" ")` at two other sites                       UX-429
§3f   70,577 px / 33,835 words at 1,202 elements,
      budget 34,000 / 12,000                                    UX-367
§4d   `core.bst` filled into three queries on every page        UX-369
§5a   21.6% of block characters repeated;
      sentence-splitting says 0%                                UX-371
```

Two of them carry a trap worth keeping until they get a guard.

**§5a's measurement contradicts the obvious one.** Counting duplicate
*sentences* over `textContent` finds nothing on the same page where
counting duplicate *blocks* finds a fifth. A guard for §5a that
measures the easy way will pass forever.

**§3g's trap runs the other way** — 795,371 B against a 4 MiB bound,
on 15,650 tracks nothing bounds. The easy guard reads `TRACE_BUDGET_B`
and checks the trace against it, which is the instrument under
suspicion grading itself. A guard for §3g must count tracks in an
emitted trace and must redden on a mutation that raises the track
count while leaving the bytes alone.

§6a is the argument the other borrowings are drawn from, so its row
names the guard that holds its *refusal* rather than one restating
their clauses — a section that did that would be a fifth copy of four
numbers.
