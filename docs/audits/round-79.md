# Audit round 79: the controls, walked — and the suite, weighed

Run on 2026-09-02, after the sibling's rounds 75-76 closed the
round-74 process slate (and its rounds 77-78 measured and
implemented three field reports, `UX-518`..`UX-521`) (`UX-500`..`UX-506`, plus `UX-507`..`UX-517`
of its own) with the implementer agent running three real tracks.
Four asks: what more the workflow can shed; every control of
`bga view` audited in a browser for reachability, usability, logic
and duplication; the `resource_blast` table that grows a second
table under itself when "All rows" is pressed, and whatever else
behaves like it; and which surfaces grow without bound as a project
gains elements or a store gains runs.

## The workflow, one round later

Rounds 75-76 measured what round 74 asked them to, and the numbers
say where the next cut is:

```text
UX-500, Regime A only     7 items · 15 suite runs · ~80 min of gate
  caught by the per-item suite        5
  outside test-touching's set         2   (both census guards)
  reached main past a green suite     2   (CI-only classes; UX-515)
implementer tracks (round 75)          3 · 943-1,174 s · 81k-131k tokens each
first read after the rules card        37,679 B → 7,401 B
```

And where the suite's minutes go, read from CI's own reference:

```text
tests/ci_reference.json      400 files · 1,330 serial seconds
browser-tier files            40 files · 685 s · 51 %
top 12 files (all browser)             432 s · 32 %
files under 1 s              259 files ·  36 s ·  3 %
collection, 5,897 tests                 12.5 s wall
```

Four filings follow from those two tables. `UX-522`: the selector
unions a fixed **census set** (the guards that read the whole tree
and name no module — exactly the two misses) and runs from a
pre-commit hook, so the last edit is the one it always sees.
`UX-523`: forty browser files each export and boot the same page;
one export per fixture per session and one Chromium per worker is
the single largest cut available — half the suite's seconds are in
those forty files. `UX-524`: CI already knows which tests executed
which module; a coverage-derived touching map adopted the `UX-503`
way closes the import-chain class the grep cannot see. `UX-525`: a
track's 81k-131k tokens have no split by phase, and the levers
differ per phase.

The reading of `UX-500` so far: Regime B has not been run, and the
two census misses are the reason it could not have been trusted;
`UX-522` is what makes the next Regime-A count a fair test of it.

## The controls, walked

The page under audit had both planes: the ex06 cold capture (813
hook processes, spine on), exported and served, 65 sections and
**782 controls in 193 classes**; the warm run beside it as the
one-plane contrast (32 sections, 293 controls, and the page says
"Plane 2 not captured" where it should). Every class was driven
once in Chromium with the DOM diffed before and after.

Reachable: every class is Tab-focusable except those inside a closed
fold, which are reachable after opening — and the folds announce
their depth and row count before the click (§3a holding). Usable and
logical: the jump box, Prev/Next/Top, Collapse/Expand all, the 46
JSON doors, the 185 `?` descriptions, the 52 inspect links, the 23
Top-N selects, the filters, the 29 copy controls, the 13 Expand
controls (which *move* the table into focus and back — 95 tables
before, 95 after, never a copy), the reader select, the what-if
boxes, the Perfetto substitutions. Plane 2 rendered: `plane2_coverage`,
`binary_cost` (71 rows), `by_binary`, the per-element "What Plane 2
saw" folds on nine cards, the `pinned_to_one_job` flag.

What did not hold: Focus answers 25,501 px above the button with no
scroll and no acknowledgement (`UX-534`); one preference drawn as 29
unsynchronised checkboxes, 65 unnamed collapse buttons, unannounced
accelerators, and a two-plane question answered with zeros on a
one-plane run (`UX-536`). And the served page shows the
**capture-time** analysis: six Plane 2 terms, the `restructuring`
section and four findings that a fresh analysis of the same run
produces are absent, and nothing on the page can say so — the
producer stamp reads 0.3.0 on both (`UX-533`).

Duplication, counted: 12.8 % repeated characters over the cold
export (§5a's budget is 21 %), `core.bst` named 54 times in 22
sections — citations, by design. `UX-390` verified closed. The
remainder is three real duplicates: `producer` published under two
payload paths and drawn twice, the rail listing "Producer" and
"Latent heavies" twice each, and `graph_summary` repeating three of
`graph_metrics`' sentences (`UX-535`).

## "All rows", and its class

Neither real capture publishes `resource_blast` (one local source
per element; the section needs a resource shared by two), so the
table was reproduced on a copy of the snapshot given sixty shared
resources — enough to cross the 40-row bound. Then the mechanism:

```text
outer tbody before any click     624 direct <tr>   60 published + 564 torn out of 54 nested tables
nested fold tables                 0 rows           "Blast elements · 1 level, 11 rows" opens empty
after All rows                   624 visible · badge "624 of 60" · "Copy 624 rows"
```

There is no second table. `tables.js:77-78` selects the outer
tbody and then `querySelectorAll("tr")` — every row at any depth —
and `:131-132` re-appends what it kept to the outer tbody, so the
folds' key/value rows migrate up and render beneath the real rows
as two-cell rows: the "separate table below". The same descent is
in sort, Top-N, the element stamp, the badge, the copy count and
the distribution strip. On the real cold page two tables are
already wrong at rest (`serialization_point_risks` badge "3 of 1",
`run_instance.producer` "25 of 3"); with a fresh analysis, five.
`UX-366`'s guard stays green because no fixture has a bounded table
with a nested table in it — the exact shape `UX-403`'s census warns
of (`UX-532`).

## What grows

Three axes, each built rather than read: elements (seeded runs of
14, 122, 1,202 and 4,002), runs (the ex06 snapshot copied 2, 20 and
100 times into a store), and Plane 2 processes (the cold capture's
813 records, and the same ×10 under offset pids). Every page counter
was taken in Chromium with every chapter and fold open.

**Elements.** Thirty-seven leaf sections are flat within ten nodes
across all four sizes — the 40-row bound (`UX-366`/`UX-419`), the
24-card cap, the rail's eight and the jump box's eight all hold. Four
surfaces do not:

```text
                       @14      @1,202     @4,002    budget "to 4,000"
nodes                3,528     24,345     73,075     27,500   2.7×
words                8,061     37,312    107,352     41,000   2.6×
controls               573      1,949      4,774      2,300   2.1×
```

Three tables (`elements`, `wall_clock_share_us`, `leaf_analysis`)
keep every row in the DOM hidden past the bound, and the Perfetto
"Ask about element" `<select>` carries one option per element —
4,002 of them. The volume budget asserts its "to 4,000" class on a
run of 1,202 and is breached by two to three times at the class's
own top (`UX-526`, `UX-527`). The data half of the export is 427 B
per element with only the 8 MiB reporting ceiling above it, and
every hidden row is in the page twice — once as JSON, once as a
`<tr>` (`UX-529`). `bga analyze` itself is n^1.6-1.9: 45 s at
4,002 elements, paid by `bga view` on any run without a published
analysis (`UX-531`).

**Runs.** The export embeds no store and is O(1) in N. The served
page is not: at a hundred snapshots the run picker has a hundred
options, the store exhibit a hundred and one rows and two hundred
SVG children, `store.json` 159 KB — while the history sparklines
beside them were windowed to twelve points. `UX-394` was filed with
two runs in the store and never saw the axis (`UX-528`).

**Processes.** Plane 2 is bounded on the page — the redundancy
findings at 40, the per-element maps under the pair bound, node
count invariant between 813 and 8,130 processes — except the trace:
at 8,159 tracks the export refuses the timeline whole rather than
trying the `--planes 1` its own recipe names, and the spine's second
slice per process halves the room before that (`UX-530`). Three
Plane 2 blocks still reach no page at all: `static_census`,
`commands_not_observed`, `declared_vs_used` — one, zero and zero hits
in the export — which is `UX-389`'s finding one round after its
close.

## Filed

Fifteen. Workflow: `UX-522` (the selector runs last and carries the
census — High), `UX-523` (forty files boot the same page — High),
`UX-524` (the touching map measured in CI — Medium), `UX-525` (a
track's tokens by phase — Medium). Growth: `UX-526` (the budget
class breached at its top — High), `UX-527` (an option per element
— High), `UX-528` (the store section grows with every snapshot —
High), `UX-529` (the data half, unbounded and twice — Medium),
`UX-530` (the track ceiling met by a real capture — Medium),
`UX-531` (analyze superlinear — Medium). Controls: `UX-532` (the
table tools read nested rows as their own — High), `UX-533` (the
served page is the capture-time analysis — High), `UX-534` (Focus
answers far above — Medium), `UX-535` (one fact twice — Medium),
`UX-536` (four controls that say less than they do — Low).

## Standing

Verified and not filed: Expand moves and never copies; the JSON and
`?` doors revert cleanly both ways; every drawing's table twin is
pre-rendered; Collapse/Expand all drive both layers; the preset
select replaces its table; the export hides the served-only
controls; thirty-seven of forty-one leaf sections are flat from 14
to 4,002 elements; Plane 2's page surfaces are invariant from 813
to 8,130 processes. The round's own cost: three agents, ~610k
tokens between them, the largest the control walk at 336k — which
is the figure `UX-525` asks the implementer tracks for.
