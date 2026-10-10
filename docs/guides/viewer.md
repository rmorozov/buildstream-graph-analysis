# The browser report

What `bga view` draws, chapter by chapter. Every other command is in
[`cli.md`](cli.md); the documents the page reads are
[`json-contracts.md`](json-contracts.md).

## `bga view` — the report in a browser (`UX-193`)

```bash
bga view                 # @last, opens a tab
bga view @prev --no-browser      # prints the url instead
```

A local page over one run's published JSON. `127.0.0.1`, a port the
kernel picks, and a fixed allowlist of documents — nothing else in the
run is reachable, there is no directory listing, and no write method is
answered.

**It moves between runs** (`UX-394`). Three of those documents take a
parameter:

| | |
| --- | --- |
| `blast.json?target=…` | what one element rebuilds |
| `whatif.json?elements=…` | what fixing a set would be worth |
| `?run=<stamp>` | **which snapshot the whole page is of** |

`bga view` is started on one run, but it serves any snapshot in that
project's store: `?run=20260101T000000Z` builds that run's documents on
demand and the page renders them. The rail draws a picker when the
store holds **two or more** — below that there is no choice to offer,
so there is no control. `?run=` naming a stamp the store does not have
falls back to the run the server was started on, rendered whole rather
than an error page.

The stamp is in the URL, so a link to a run is a link somebody else can
open, and the browser's back button moves between runs.

**The picker is windowed** (`UX-528`). `store.json` carries the last
`STORE_WINDOW = 12` snapshots, not the store: at 100 snapshots the
picker drew 100 options, the store trend 100 rows, and `store.json` was
34,056 B against 4,121 B at 12. The rest is a second document,
`store-all.json`, offered in the manifest and fetched only when a
reader asks for "show all N snapshots" — so a long store costs the page
nothing until it is wanted. A run outside the window is still
reachable: the picker grows a box that takes a stamp, which is the same
`?run=` the menu follows. The window is the same 12 the element
sparklines use (`HISTORY_POINTS_MAX`), because it is the same question
— the last dozen runs of this project.

An **export has no store** — it is one file over one run — so it
renders no picker at all.

**It renders the schema, not the report.** The page asks
`schemas.json` what each key *is* — a duration, a share, a findings
array, a table with these columns — and renders from that. Two things
follow, and both are deliberate:

- A field added to `analyze/v7` appears in the viewer with **no change
  to the viewer**.
- Anything the viewer should show has to enter the published schema
  first, where `--format json`, CI and every external consumer get it
  too.

The page is a handful of files checked into the repository under
`bga/viewer/` — HTML, one stylesheet and a few ES modules — with no
bundler, no npm and no build step. A richer TypeScript app is a welcome *consumer* of these
payloads rather than a replacement: the view-hints below exist so one
can be written without this project blessing a frontend stack.

### Three views that draw (`UX-196`)

The page carries three things a table could not say:

- **The band.** Compare's noise band as a strip, the baseline runs as
  dots, the candidate as a marker. `UX-170`'s **disputed region** — a
  candidate outside the band but inside the range the baselines
  themselves spanned — took a paragraph in prose and read like a
  paradox; drawn, the marker simply sits between the strip's edge and
  the dots' extent. `bga view RUN --compare BASELINE` draws it against
  `BASELINE` (an alias, stamp prefix or path) instead of the run before
  `RUN` in the same store.
- **The store trend.** `--list` made visual. Snapshots that are not
  measurements (failed, interrupted, suspended) are drawn as squares
  rather than dropped — they are on the disk, so they are on the chart.
- **The blast explorer.** A box taking a url, a path or an element
  name, answered by `blast.json?target=…`, which calls the same
  function `bga blast` calls. The served answer is byte-identical to
  `bga blast --format json` (`--no-cost`, because a page should not
  block on the full pipeline).

Exactly two custom SVGs, no library behind either, and nothing
recomputed in the browser — the payloads already carry the band edges,
the observed extent and the verdict.

```bash
bga snapshot --list --format json     # store/v1, what the trend draws
```

The text listing and this JSON render from the same rows, so the
drawing and the terminal cannot disagree about what is on disk.

### What the page leads with (`UX-202`)

Above the sections, two things a list of tables could not say:

- **The evidence header** — confidence and its band, Plane 2's
  coverage, the host line, and the run's incompleteness. `UX-156`'s
  tone: what this capture can and cannot support, stated *before* any
  number is believed. A failed, interrupted or suspended run says so
  here rather than in a banner floating above an otherwise ordinary
  report.
- **The overview waterfall** — the real duration, down through the
  attribution gaps to the certified floors, each segment labelled with
  its published number and linked to the section that explains it.

**Every number in both is read from a published field.** Nothing is
computed in the browser; the one division in the waterfall is a CSS
width. A gap the JSON does not carry enters `analyze/v7` first, where
`--format json`, CI and every other consumer get it too — which is why
`confidence.band`, `run_instance.incomplete_reason` and
`plane2_coverage` are fields rather than viewer logic.

### Whose analysis the page is showing (`UX-533`)

```bash
bga view @last --reanalyse    # analyse with this build, not the capture's
```

The page serves the analysis the **capture** published, so a run
captured by an older build renders that build's answer. The evidence
header says which: *analysed at capture by bga X*, *analysed here by
bga X*, or — when the stored file records a contract set this build has
moved past — the same sentence plus how many of `analyze`'s always-published
sections are absent from it, and the command to re-run with.

`--reanalyse` is that command. It analyses the run with this build and
serves that instead; the stored file is **read, never written**, so the
page and the CI comment that quotes the stored analysis do not diverge.
Staleness is `UX-249`'s contract set — a build that moved nothing
publishes the same set — not a version comparison.

### Finding your way around it (`UX-199`)

Every section carries an `id`, a generated table of contents sits at the
top, sections collapse (and remember it), and a jump box finds an
element by name. An exported report keeps all of it, plus the questions
page inlined and the blast search box hidden — it asks a server, and an
export does not have one.

### What the page opens with (`UX-207`)

The first screen is a **decision**, and everything below it is the
evidence for that decision. `analyze/v7` publishes a `headline` block —
the diagnosis (`chain_bound`, `scheduler_bound` or `inconclusive`), the
ratio it was decided by, what the opportunity is worth, and the three
elements to look at first, each pointing at the finding that reasons
about it. The panel renders that block; it derives nothing, so the
terminal, CI and the page cannot disagree about what should be fixed
first.

### Sections named as questions, and a rail (`UX-209`)

Sections are titled by the question they answer — *"Where did the
wall-clock go?"*, *"How much faster could this build possibly be?"* —
with the schema key kept as a muted subtitle so an anchor pasted into
an issue still reads. The question is a schema declaration
(`bga:question`), not a viewer table, so it reaches the text renderer
too.

The contents groups those sections into a rail rather than listing them
in payload order:

```text
decide       what this run concluded, and what to fix first
act          where the wall-clock went, which elements bind
prove        the floors, the capacity verdict, what did not add up
investigate  the graph's shape, one resource's blast radius
raw          the capture's own identity
```

A section whose schema declares no rail lands in `raw` — never nowhere.

### One click from investigation (`UX-208`)

- A column can declare that it holds element uids (`role: "element"`),
  and every row of such a table earns the same **Inspect** — jump to
  that element elsewhere in the report, and open it in Perfetto where
  there is a timeline. One loop in the renderer, no per-table code.
- Critical-path boxes carry a popover with the element, its kind, its
  duration and its share, read from the published entry.
- Every SQL block has a **Copy** button.
- Tables get a `Top 10 ▾` preset over any declared quantity column; the
  badge still says `10 of 1,202`, because a reader who cannot see the
  denominator cannot tell a filtered table from a small one.
- The blast box opens with the payload's top-ranked targets as chips.

### What to run next (`UX-218`)

The report ends with the next commands, chosen by what this run
measured, with the run path and the element already filled in.

Verbatim from `bga gen-synthetic --store /tmp/bga-demo` then
`cd /tmp/bga-demo && bga analyze @last`, 2026-09-03 (`UX-577`) — the
seed store `UX-330` plants, so this block is **reproducible, not
kept**: the same two commands print the same eight lines on any
machine. It used to quote a stamp from an `examples/06` store that no
clone has, advising a `compare` that store refused with exit 6.

```text
Next:
  layer02/mod001.bst is the longest thing on the critical path at 14.4s, 54% of it - the build cannot finish sooner than this chain.
    bga blast layer02/mod001.bst @20260303T091500Z
  layer02/mod001.bst is the first thing to fix, worth 6.6s - this is what changing it rebuilds.
    bga blast layer02/mod001.bst @20260303T091500Z
  Make the change, then capture it the same way - run it in /tmp/bga-demo.
    bga snapshot -- bst build all.bst
  Whether it helped, judged against this store's noise - run it in /tmp/bga-demo.
    bga compare @prev @last
```

Both runs of that store are full runs, which is why the last line is
offered at all: `UX-78` refuses a full baseline against an incremental
candidate with exit 6, so a store whose `@prev` and `@last` differ in
`run_mode` is advised the newest run that *does* pair —
`bga compare @<stamp> @last` — or, where the store holds no such run,
is not advised to compare at all (`UX-577`).

Every line under a reason is a command as `bga` would receive it, and
`UX-326` is why that is worth saying: for six rounds the last two were
not. `bga snapshot <project>` put the project where the *build command*
goes and crashed; `bga compare … --project` named a flag `bga compare`
does not have. Both are now parsed by the parser that would receive
them, in
[`tests/unit/test_the_printed_sentences_are_contracts.py`](../../tests/unit/test_the_printed_sentences_are_contracts.py).

Same list in `--format json` as `next_steps`, and in the page's
decision panel with a Copy button beside each — one function, so the
terminal, CI and the page cannot advise differently.

**Which** step is right depends on the run, so it is decided in the
pipeline rather than by whatever is reading the report. A chain-bound
build is not told to add builders. A run outside a store is not told to
compare against a previous one it does not have. A run with no Plane 2
report is not told to look inside its elements. Each step names the
published field it follows from, so the advice can be checked against
the number behind it.

### Findings show their evidence (`UX-217`)

Each finding renders the numbers it was drawn from, in the units the
schema declares them in:

```text
⚠ 12.5% of wall-clock is untracked tail
   category      untracked_tail_us
   category_us   2 ms
   share         12.5%
```

Those are published fields, in published units — `share: 0.125` is a
share and renders as a percentage; `category_us: 2000` is microseconds
and renders as a duration. A finding whose evidence key the schema does
not describe renders it raw rather than guessing at a unit.

### Everything about one element, in one place (`UX-216`)

Every element the report discusses gets its own section: what it holds
of the critical path, what a fix is worth, what it rebuilds, and —
where Plane 2 saw it — how busy the cores were, how many jobs it asked
for and what it peaked at. The findings that name it are there, and so
is what joins the critical path if you fix it.

Every mention of an element links to it: a table row's **Inspect**, a
critical-path box, a finding's element list, a top action, a blast-tree
row. A section says where else in the report the element appears, read
from what the page actually drew.

`bga view` before this shipped 19 Inspect affordances on `examples/06`
that resolved to nothing — the anchor scheme and the ids never matched.
The guard now resolves every one of them.

### A link that shows what you were looking at (`UX-211`)

**Copy link to this view**, beside the contents. The filter, the
thresholds, the sort, the Top-N, the collapsed sections and the folds
travel in the URL fragment, so what lands in the issue is the view you
built rather than the unfiltered wall. `#floors` still means exactly
what it meant; the state follows a `~`. The hash wins where it speaks
and your own remembered state stands where it is silent — and it works
from an exported `file://` report, where browser storage may not exist
at all.

### Verdicts without the palette (`UX-212`)

The trend's dots differ by **shape** as well as colour — one per
verdict kind, from a map the schema declares — and the band's noise
strip and observed extent differ by outline. Both survive a grayscale
print and a colour-blind reader.

### Interrogating the tables (`UX-205`)

Each table gets a filter box with a row-count badge (`12 of 1,202`) and,
on every quantity column, a threshold typed in that column's own unit:

```text
> 5s        on a duration column
>= 512mb    on a size column
< 10%       on a share column
```

The unit parses because the schema *declares* what the column is — and
the comparison runs against the published value, never the formatted
text. A cell copies on double-click as its raw value; **Copy shown
rows** puts the filtered rows on the clipboard as JSON that parses.

Measured at 4,000 rows: 146 ms to render, 20 ms to filter. There is no
windowed rendering, deliberately — machinery without a measured need is
how a thin viewer stops being one.

### Two drawings, and no DAG viewer (`UX-206`)

- **The chain, drawn** — the critical path as a sequence of boxes whose
  widths are the published `share_of_path`. Long chains fold in the
  middle (`UX-187`'s fold) and open in place.
- **The blast tree** — a blast answer as an indented hierarchy, direct
  consumers first, then the closure by depth, each row with its kind
  and measured work. The depth is published in `blast/v2` as
  `blast_tree`; the page does not walk a graph.

A general BuildStream DAG rendering stays deliberately unbuilt — it
answers no question anyone asks. The argument is in
[Direction 7](../design/directions.md).

### The report as one file (`UX-195`)

```bash
bga view @last --export report.html
```

The same page, as an attachment: the run's JSON inlined, the CSS and
both modules inlined, the timeline carried as a `data:` URL. No port, no
server, no network — it opens from a downloads folder, a CI artifact
viewer, or an email.

**A large document travels compacted** (`UX-529`). Past
`DATA_COMPACT_MIN_B` — 200,000 B of JSON — a payload is written as one
gzipped, base64-encoded `application/octet-stream` block instead of
readable JSON text, and the page inflates it on load. Nothing is
refused and nothing is dropped: it is the same document, and a reader
does nothing about it. Measured on the two seeded runs
(`bga gen-synthetic --seed 1`, and the same with `--layers 20
--width 200`):

```text
elements   report.json   gzip+base64   ratio
   1,202       628,335        69,172   0.110
   4,002     2,041,945       193,492   0.095
```

The threshold sits above both committed fixtures (30 KB and 80 KB of
data), so the small exports a person reads in an editor stay readable
and the large ones a person mails stay mailable.

**What it weighs, in three parts.** A report is not "page plus data":
it also carries the JSON Schema for every document in it, so a reader
can ask what a number means with no network. That third part travels
whole whether or not a run has the rows it describes, which is why it
is counted separately (`UX-342`).

Measured in round 65 on a cold two-plane capture of `examples/06`
(38 s, `bga snapshot -- bst build all.bst` against an isolated
`XDG_CACHE_HOME`, then `bga view <run> --export report.html`):

```text
total       520,048 B   508 KiB
  source    283,979 B   54.6%   the modules and the stylesheet
  contract   81,623 B   15.7%   the embedded schemas
  data      154,446 B   29.7%   the payload and the inlined timeline
```

And on the 1,202-element synthetic run
(`bga gen-synthetic /tmp/scale --seed 1`), same round:

```text
total     1,197,665 B  1170 KiB
  source    283,922 B   23.7%
  contract   81,623 B    6.8%
  data      832,120 B   69.5%
```

**Source and contract are the same bytes on both runs** — they are the
page, and a bigger project does not make them bigger. What scales is
the data. On a small project the page is the larger half; on a real one
the data passes it and keeps going, which is the ratio the thinness
rule is about.

Both data figures predate the compaction above: round 80 (`UX-529`)
took the 1,202-element run's data half from 629,385 B to 70,222 B and
the 4,002-element one from 2,042,989 B to 194,536 B. The shape of the
statement is unchanged — the data is still what scales — but the
constant in front of it is an order of magnitude smaller.

> Round 21 measured 638 KiB with the page at 6.0% on the same synthetic
> run, and round 23 measured 158 KiB with the page at 90,611 B on
> `examples/06`. Both are superseded by the figures above — kept
> because a dated measurement is evidence about when the page grew, and
> `UX-132`'s rule is to mark such a figure rather than to rewrite it.
> The page has roughly tripled across rounds 24–64 (the decision panel,
> the rails, the chapters, the table tools, the shape channel, the
> query library) and the embedded contract is new since round 51.

Four ceilings, and they are not all in the same unit. Two are byte
bounds on what is *carried*; one is on what Perfetto has to **draw**,
which is what actually decides whether a big capture opens (`UX-430`);
and one is on the page `bga` itself writes, whatever the run
(`UX-1052`). None is enforced by refusing to write your report — a
report that large is still your report — and each says which one it
was:

| constant | the bound | measured against | when it is the one that bit |
| --- | --- | --- | --- |
| `EXPORT_BUDGET_B` | 8 MiB | the whole written file: source + contract + data | nothing to do; the note says an attachment may not survive it |
| `PAGE_BUDGET_B` | 166,750 B | the **page half**: the file less its data blocks — `index.html`, the stylesheet, and the viewer module gzipped with its loader (`UX-1052`) | nothing; it bounds the viewer `bga` writes, never your run. `--export` prints the page and data halves apart, and a release is held to it |
| `TRACE_BUDGET_B` | 4 MiB | the **gzipped trace** before it is base64-encoded — one part of the data half | the trace is left out and the page names the bound; `bga timeline` renders one beside the snapshot |
| `TRACE_TRACK_BUDGET` | 8,000 tracks | the rows Perfetto opens: one process track per element, one thread track per traced pid — **processes**, not slices, so the spine's second record of one process is not a second row (`UX-406`) | nothing, for an export: it renders again with `--planes 1` and the handoff sentence says it did (`UX-530`). For `bga timeline`, `--planes 1` or `--only-element` narrow what is *drawn* rather than what is carried |

The third is the one a reader is least likely to guess at, because the
byte figure looks fine when it bites: measured on the seeded scale run
at twelve processes an element, the trace is **491 KB against a 4 MiB
bound and 16,832 tracks** (round 83's re-measurement, the same one the
table above carries). `--planes 1` drops the process lanes and is
a 14x reduction there — and 26x at twenty-four processes an element,
since Plane 1's own track count does not move with the process
population (`UX-445`).

`TRACE_TRACK_BUDGET`'s value is one sample and says so — see its
docstring in `tools/bga_view.py`, and `UX-445` for what is still
unmeasured about it.

Since `UX-530` an export **degrades before it refuses**: it renders the
whole timeline, and if that is over either bound it renders again with
`--planes 1` and carries that instead, saying which step it took and
what the whole one would have drawn. Refusal is what is left when every
step `bga timeline` offers is still over. Measured on a capture of the
item's own shape — 8,140 processes over four elements:

```text
both planes    8,152 tracks   8,146 slices     over the 8,000 ceiling
--planes 1         7 tracks       6 slices     carried
```

For CI, put it beside the comment step — see
[`ci-comment.md`](ci-comment.md).

### The Perfetto handoff (`UX-194`)

```bash
bga view --perfetto      # skip the report, hand the timeline straight over
```

`bga view`'s page carries an **Open timeline in Perfetto** button when
the run has one, and `--perfetto` goes there directly. Below 4 MiB the
trace crosses **tab to tab**: the page opens `ui.perfetto.dev`, pings
until it answers, and `postMessage`s the bytes.

**Above 4 MiB compressed, Perfetto fetches it instead** (`UX-299`).
Carrying the trace costs at least two copies of it inside the report
tab — `arrayBuffer()` materialises the whole response and `postMessage`
structured-clones it — before Perfetto decompresses a third in its own;
the `?url=` deep link has none of them. The page finds out which case
it is in with a `HEAD` at the moment you click, because knowing the
size any earlier would mean rendering the trace, which is exactly what
`bga view`'s startup no longer does. The same 4 MiB decides whether
`--export` inlines the trace: above it the exported page says the
trace's size and carries this command instead of the bytes.

**Nothing is uploaded.** It looks exactly like an upload — a public URL
opens and your build data appears in it — so it is worth saying plainly:
ui.perfetto.dev is a static site, the trace is processed in your
browser, and there is nowhere for it to be sent.

The bytes go over gzipped, which Perfetto sniffs itself. Measured on a
real capture of `examples/06` (871 events, both planes merged):

```text
272,964 B  ->  24,782 B   (9.1%, 11x smaller)
```

`--perfetto` needs the server alive while the tab fetches the trace, so
it does not exit the moment the browser launches — Ctrl-C once Perfetto
has it. A run with no raw Plane 2 log has no timeline to hand over and
exits **7** rather than opening a page that would 404.

The handoff page also carries a list of **questions worth asking in
Perfetto** (`perfetto.html`, under the button that opens the trace they
ask about) — eighteen paste-ready PerfettoSQL queries, with a control
that swaps in whichever of this run's elements you are asking about.
They are docs, not a feature: the SQL engine is Perfetto's. `UX-373`
merged them in from the separate `sql.html`, whose URL still redirects
here.

**When to press the button.** The report has no time axis: every number
in it is a total, a per-element aggregate or a ranking. So a question
that needs *when*, or needs one individual **process** rather than the
element around it, is a question for the trace — and one that does not
is already answered on the page. Ten of the eighteen canned questions
genuinely need the trip; eight are sharper instruments for something
the page has said already.
[`what-the-viewer-answers.md`](what-the-viewer-answers.md) sorts them,
names the three places the report holds the element's answer and the
trace holds the process's, and says which of the eight
[roles](../design/roles.md) the trip actually serves — R1 and R2 only.

**Format**: `bga timeline` writes **Perfetto's own TrackEvent protobuf**
by default, gzipped as a stream, with `--format chrome` for the legacy
Chrome JSON that `chrome://tracing` and any pipeline already parsing it
still want (`UX-298`). Direction 7 argued for the JSON and named its
revisit trigger; `UX-298` is that revisit, so the argument to read now
is the one in `UX-298` rather than the direction that preceded it.

### View-hints v1

Annotations in the JSON Schema, so a renderer does not have to guess
what a number means. JSON Schema ignores keywords it does not know, so
a hinted document validates exactly as before, and `UX-190`'s rule
applies — adding a hint is an addition; changing what one *means* is a
version bump.

| Hint | Says |
| --- | --- |
| `bga:quantity` | `duration_us`, `bytes`, `share`, `count`, `seconds`, `ratio` |
| `bga:severity` | this array is findings; that key carries the severity |
| `bga:columns` | column order for an array of objects |
| `bga:direction` | `lower_is_better` / `higher_is_better` / `neutral`, for signed deltas |

Read them straight out of the tool:

```bash
bga analyze --schema | jq '.properties.total_duration_us'
# { "bga:quantity": "duration_us" }
```

A quantity outside that closed set, or a hint on a key the document
does not declare, is refused when the schema is built — a mistyped hint
is invisible at the point of use, because the renderer just falls
through and prints a plausible-looking raw number.
