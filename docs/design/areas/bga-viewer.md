# The viewer axis (rounds 21-26)

Moved from [`docs/design/architecture.md`](../architecture.md)'s
viewer chapter (`UX-689`); the chapter count, the value rule and
the module map stay there, where their guards read them.

The three planes above are how `bga` *measures*. Rounds 21 onward built
how it is *read*, and the shape is deliberately small.

- **`bga view`** serves the run on `127.0.0.1` at a kernel-chosen port
  and opens a browser at it. The server is a `ThreadingHTTPServer` with
  a fixed document table: each url is a payload computed by the same
  functions the CLI calls, so nothing is analysed differently. One entry
  is conditional rather than fixed - `store-all.json`, the whole store
  behind the windowed `store.json` (`STORE_WINDOW = 12`, `UX-528`),
  offered only when the window hides something and fetched only when a
  reader asks for it. Three
  urls take a parameter - `blast.json?target=` and
  `whatif.json?elements=`, both of which call the function their
  subcommand calls, and `?run=<stamp>` (`UX-394`), which chooses
  **which snapshot the whole page is of**. The server is started on one
  run and serves any run in that project's store, building its
  documents on demand; the stamp is the state, so a run is a link. The
  rail draws a picker only where there is a choice - two or more runs -
  and an export, which has no store, renders none.
- **Startup computes nothing large** (`UX-296`, Direction 15's first
  rule: *capture computes, view serves*). Nothing on the path to the
  socket may do O(events) work, and a large artifact is opened only to
  stream its bytes. So the report is the analysis `bga snapshot`
  already ran and published beside the run (`analyze.json`); the store
  aggregate reads the capacity scalars from the store row, written at
  capture time (`plane2-resource.json`), rather than re-parsing every
  snapshot's Plane 2 report for two floats; the noise band reads each
  baseline's `run-context.json` instead of re-analysing it; and the
  timeline is *offered* from a file test and rendered at the first
  request for its bytes, into a file the handler streams in fixed
  chunks - and that file is **Perfetto's own format** (`UX-298`):
  protobuf TrackEvent, gzipped by the writer as the packets are
  emitted, so the render is the served file and nothing passes over it
  twice. A `Trace` is `repeated TracePacket`, which is why it can be
  written that way at all; the legacy Chrome JSON stays behind
  `bga timeline --format chrome` for `chrome://tracing`. There is no
  protobuf dependency - the wire format is varints and
  length-delimited fields, and every field number is pinned to
  upstream's own `.proto` by a committed fixture, because a wrong
  number is silent. Measured on a generated 247 MB report of a million process
  records: 17.04 s and 1232.9 MB to reach the socket, against 0.04 s
  and 39.5 MB after - and viewing a 2 MB run *beside* it cost 1233.5 MB
  before and 39.8 MB after, because the aggregate used to walk into its
  neighbour's monolith. A run whose capture published no analysis is
  still analysed here from Plane 1; its Plane 2 report is refused above
  a size bound with the sentence naming the command that publishes one.
- **The page obeys a policy the server sets.** Every response carries
  `default-src 'self'; frame-ancestors 'none'` and `nosniff`; the only
  cross-origin grant is `Access-Control-Allow-Origin` for Perfetto's
  own origin, on the trace blob alone (`UX-198`) - together with the
  **pre-flight** that grant needs, scoped identically (`UX-265`): the
  blob only, Perfetto only, `GET`/`HEAD` only, plus
  `Access-Control-Allow-Private-Network`, because a public origin
  reading `127.0.0.1` is a transition Chrome asks about by name. Two
  consequences bind
  the page: it may not load anything off-host, and it may not write a
  **style attribute** - a style attribute is inline style and the
  policy refuses it, which silently killed four of the viewer's width
  channels until `UX-263`. Drawings set style through CSSOM
  (`el.style.width`, `el.style.setProperty`), which the policy does not
  cover. Relaxing it with `'unsafe-inline'` was declined: this page
  renders element names and paths out of a build and gets attached to
  tickets.
- **The page is schema-driven.** `bga/viewer/` is hand-written ES
  modules with no build step and no framework. Sections, columns, units
  and hover text come from the *view-hints* the published schemas carry
  (`bga:quantity`, `bga:question`, `bga:columns`, `bga:rail`,
  `bga:markers`, `bga:presets`, ...), so a field that gains a
  description in `bga/schemas.py` gains a tooltip in the page with no
  page edit.
- **A view is a named filter over one table, declared not coded**
  (`bga:presets`, `UX-289`, round 38). One element table serving every
  question carried 13 columns on the 1,202-element run, and the
  questions readers actually arrive with were answered by other tables
  the payload published separately. A preset names one question and the
  four to six columns that answer it — `{name, question, from|where,
  columns, sort, bound}` — and every population is a **filter over a
  published field**: `from` reads a selection the payload publishes once
  and takes its order from it, `where` tests a column the element
  records carry. Nothing computes a membership the payload does not
  have, which is why `UX-288` came first. The preset travels in
  `UX-211`'s fragment and is named in the rail, so a view is a link.
  `PRESET_COLUMNS_MAX` bounds a view at eight columns and the schema
  validator refuses a wider one: a table that needs more than that to
  answer one question is not a view of the data, it is the data.

- **The mapping is law** (`UX-302`, round 41). The rule above is now a
  table — round 41's style guide
  ([`styleguide.md` §1](../styleguide.md)) maps published shape (+ hint)
  to the one control that may render it — and
  `bga/viewer/shapes.js` is that table as code. `classify()` returns a
  control's name; every render path asks it rather than testing shapes
  itself, so "which control draws this" has one answer and one place to
  read it. **Raw JSON on the page is a defect unless it is
  deliberate**, and there are exactly two deliberate sites: `UX-277`'s
  labelled fold, and the per-section **"view as JSON" toggle**
  (`bga/viewer/rawjson.js`) that a reader opens to paste a section into
  an issue — which works in the export, because that is who needs it. A
  shape the table does not cover renders as the fold *and* warns on the
  console naming the payload path: the gap is a design task, not an
  improvisation. `tests/unit/test_the_mapping_is_law.py` boots the real
  pages and walks every text node for JSON-shaped content outside those
  two.

- **A shape draws as a shape** (`UX-303`, round 41). Two hints join the
  vocabulary — `bga:series` for an ordered numeric array and
  `bga:distribution` for a published percentile object — and each
  carries the reading its control needs: the unit of one step, and the
  key that holds the sample count. `bga/viewer/drawings.js` holds the
  sparkline and the density strip; it imports nothing and takes its
  formatter, so the quantity table stays in `format.js`. Under three
  points is a sentence and no drawing. A table past the row bound
  wears a strip built from its primary quantity column's own
  `data-raw` values, under [`styleguide.md` §2](../styleguide.md)'s
  boundary: **a self-built strip prints no derived number** — its
  labels are actual rows and a count of rows, and the percentile ticks
  are geometry. That boundary is the no-arithmetic rule below, applied
  to a drawing.

- **Dark is the design surface, and a fill is not a text color**
  (`UX-304`, round 41). `bga/viewer/style.css` holds every color the
  product has: `:root` carries the dark tokens, `@media
  (prefers-color-scheme: light)` is the override — it also matches a
  reader who expressed no preference, so an unset browser is unchanged
  — and `@media print` renders light on white, because an export is
  attached and printed. Tokens come in two grades: **text-grade**
  (≥4.5:1 against its surface, for reading) and **mark-grade** (≥3:1
  and inside the surface's lightness band, for filling). The split
  exists because the dark set had never been validated and three of
  its four status colors were text-grade doing fill work.
  `tests/palette.py` is the validator — WCAG contrast, CIE L\*, ΔE2000,
  dichromat simulation, no dependency — and the guard pins the bands,
  refuses a hex literal outside the stylesheet, and holds every
  status-toned rule against a list naming its non-color channel
  ([`styleguide.md` §4-5](../styleguide.md)).

- **`--export`** inlines every served document and every module into one
  self-contained HTML file. Past `DATA_COMPACT_MIN_B` (200,000 B of
  JSON) a document is inlined gzip+base64 in an
  `application/octet-stream` block that `load()` inflates rather than as
  readable JSON text (`UX-529`) - the same document, one order of
  magnitude of bytes. What cannot survive the export at all - a live
  search box, anything needing a server - is *hidden with the command
  that answers it* rather than shipped as a control that always fails.
- **The no-arithmetic boundary** is the axis's one rule, and it is the
  reason the rest holds: **a viewer that derives a conclusion is a
  second analyzer.** Diagnoses, rankings, verdicts, savings, next steps
  and projections are all decided in the pipeline and read by the page.
  Where a question needs a number the payload does not carry, the page
  *asks the server* rather than computing it. Guards assert this
  directly, and the discipline is what lets the terminal, the CI comment
  and the page state one build's facts identically.

The corollary is the constraint Direction 7 wanted: anything the viewer
should show has to enter a published schema first, where the text
renderer, CI and every external consumer get it too.

