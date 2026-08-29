# Audit round 64: the walk that asks for the answer, and a page that grows without imports

Run on 2026-08-29, after the sibling's rounds 47-63 — seventeen
rounds and 170 commits since round 46, closing every filing from
rounds 45 and 46 (`UX-324`..`UX-336`), releasing 0.3.0, splitting the
viewer along its seams (`UX-337`/`UX-340`), giving the report units
(`UX-343`), budgets at scale (`UX-360`/`UX-367`), a measured capture
(`UX-375`..`UX-382`), plane2/v3 (`UX-384`..`UX-386`) and its own
outsider walk (round 63, `UX-388`..`UX-397`).

Four asks this round: review that landing; answer the JS-dependency
question `UX-397` carries; walk `snapshot → view → Perfetto` once
more, this time judging the *analytic outcome* — were optimization
directions for the project under test actually findable in every
plane; and design the test plan that catches most problems in few
rounds.

## The landing, verified

Twelve landings sampled adversarially — the eight closures of rounds
45-46's filings, and four of the sibling's own — each run green at
HEAD, then its *mechanism* reverted to see the guard go red:

| task | mutation | guard |
|---|---|---|
| `UX-333` | slice name re-truncated to `[:120]` | RED — `test_a_long_command_is_whole_in_the_name` |
| `UX-334` | a `setAttribute("style", …)` restored in `drawings.js` | RED — the served page's own `style-src-attr` report, 3 clauses |
| `UX-335` | `contained()` made to rethrow | RED — "the page still refuses as a whole" |
| `UX-324` | refusal check moved after the first write | RED — the byte-for-byte store clause |
| `UX-325` | `from tools.bga_snapshot import …` restored | RED — guard prints the offending line |
| `UX-326` | printed argv regressed to the crashing shape | RED — reproduces the exact UX-326 message |
| `UX-328` | `whatif` de-enrolled from `--schema` | RED — emitter/answer mismatch, both derived |
| `UX-343` | analyze hint loses `QUANTITY` | RED — 5 clauses |
| `UX-367` | the fold defeated (`data-open` always true) | RED — against the 1,202-element synthetic run |
| `UX-385` | detection blinded (`named_not_observed: []`) | RED — 2 clauses |
| `UX-386` | architecture claim reverted | RED — 3 clauses |

`UX-336`/`UX-337` checked structurally: `-n auto` is wired into every
Makefile tier, `make test-touching` maps a real diff to the right ten
files with `--why`, and the viewer split is real — 24 files, the
largest exactly at the 1,500-line bound where 2,614- and 2,752-line
monoliths stood.

The **plane2/v3 bump is legitimate**: made by `UX-384`, removing the
published `elements` key (99.1 % of the section's bytes at 1,202
elements) from `redundant_operations` findings — removal ⇒ bump under
the `UX-190` rule, v2 retired to the superseded set, the rule cited
in the emitter.

One scope gap survived falsification: the same unit mutation that
reddens five tests on an *analyze* hint stays green on a *whatif*
hint — the `UX-343` census walks one document. Filed as `UX-404`.
No sampled guard was red at HEAD; no sampled guard stayed green
under its mutation.

## The walk, scored against an answer key

Round 63's walk audited the page's *elements*; this round's walk
audits its *advice*. `examples/06-macro-micro-optimization` ships an
`optimized/` twin, so the intended optimizations are known before the
tool speaks — the walk reads the answer key first, then asks each
plane what it would have told a stranger.

The key, from `diff -r elements/ optimized/elements/`: **MACRO 1**,
lib-a..f are declared as a six-deep chain none of them needs —
the fix fans them out off core.bst; **MACRO 2**, every lib declares
a build dep on codegen.bst that only lib-f should carry; **MICRO**,
core.bst pins `notparallel: True` over eight ~1 s translation units.
The walk: `doctor` (23.4 s) → cold snapshot (31.9 s, artifacts
deleted first) → incremental snapshot (2.8 s) → `correlate`,
`cache-logs`, `view --export` driven in Chromium, `timeline` into a
real `trace_processor_shell` v57.2.

**Plane 1 — the class, not the edit.** "This build is chain-bound
… the way to a shorter build is a shorter chain"; core.bst is the
top card at 6.0 s; and from declared variables alone it names the
MICRO fix verbatim — "`variables: notparallel: True` … removing the
pin is a single-line change". MACRO 1 partial (right diagnosis, no
removable-edge claim — missing data, by design), MACRO 2 miss.

**Plane 2 — the whole answer key, verbatim.** Never-read edge lists
per element ("lib-b.bst never read: codegen.bst, core.bst,
lib-a.bst"), the -j1 pin with "remove `notparallel` … before
touching its sources", and correlate compressing all of it into one
paragraph with a projection: "Replaying this run with those edges
removed … finishes in 8.0 s against 20.9 s: 12.9 s". A stranger can
act on the exact `.bst` lines. Bonus color all correct: cc1plus at
76-81 % of every element's CPU, 9× redundant cmake configures.

**Plane 3 — a different, real question.** Over 79 kept logs:
configure tax 19.7 % [medium], developer tax, sandbox-tax floor.
None of the answer key — and honestly so: no graph, no scheduler
context. Its own directions are correct and actionable; at a strict
two-run history it would have said almost nothing, and says so.

**The page — everything present, the macro atomized.** The headline
is right ("chain-bound"), the #1 card is right, the MICRO sentence
renders whole. But the macro evidence is seven element folds the
reader must aggregate — correlate's one-paragraph synthesis and its
12.9 s projection reach no section (zero grep hits in the export for
"Replaying this run"). One caption actively inverts its computation
(`serialized_pairs`, `UX-408`).

**Perfetto — one real addition, four wrong answers.**
`waited-on-flow` for lib-b gives the per-edge evidence no other
surface has: lib-a slack 0 ms (binding), codegen slack 8,009 ms
(finished 8 s before lib-b started) — MACRO 1+2, per edge. But with
the spine on, every process is two slices: the concurrency counter
peaks at 44 against a published `max_concurrency` of 24, and three
more canned queries answer ~2× or negative (`UX-406`).

**The verdict the round was asked for:** directions were genuinely
findable in all planes — Plane 2 names the entire key, Plane 1 the
class, Plane 3 a real orthogonal direction, Perfetto one direction
nobody else gives — but the walk's "all planes" held only because
the capture was re-run from inside the project: the documented
relative `--project` shape had silently forfeited every Plane 2
byte first (`UX-405`), which for a stranger turns "all planes" into
"one plane". And where the answer was weakest, the cause splits
cleanly: missing *data* (Plane 1's edges), missing *synthesis* (the
page's macro), and wrong *rendering of present data* (the spine
double-count) — three different fixes, three different filings.

## The library question, answered with a measurement

`UX-397` carries one argument for adopting Tabulator: sorting,
filtering and virtual scrolling "in one dependency rather than in
twenty-one modules." Measured, the premise is wrong:

```text
$ grep -l 'renderTable\|buildTable' bga/viewer/*.js
bga/viewer/app.js          the caller
bga/viewer/primitives.js   the factory's parts
bga/viewer/structured.js   the factory
```

All 31 tables flow through one factory, which already owns declared
column specs, declared-not-sampled sorting, the 22 preset menus,
Top-N, fold-the-middle, the density strip and the copy control. The
21 modules consume it; none hand-rolls a table. The marginal cost of
`UX-392` is one factory change that every future table inherits —
the economics a library promises, already owned. Against: 400 KB on
a 477 KB export, a styleguide whose guards assert *this* DOM, a
console guard (`UX-334`) that inline-styling libraries would light
up, and no toolchain to carry a dependency's lifecycle.

The recommendation filed as `UX-398`: no library now, and the
standing question replaced by a standing *rule* — a dependency is
admitted when a behavior cannot be met by factory + platform within
the volume budget (measured before/after on the export's page half)
and the library's wiring-plus-conformance cost measurably undercuts
the in-house cost. The trackevent writer is the named precedent.

## Growing the UX without importing the world

Five routes, each already half-proven in this repo:

1. **The factory, not the fleet** — every table/drawing ask lands in
   `structured.js`/`drawings.js` once and amortizes over 31 tables
   and 44 sections. No per-section rendering code, ever.
2. **The browser is the library** (`UX-399`) —
   `content-visibility: auto` is virtual scrolling for zero bytes;
   `IntersectionObserver` is `UX-393`'s scrollspy in ~30 lines;
   native `popover`/`<dialog>` retire overlay plumbing; `:target` +
   `scroll-margin-top` fix every deep link under sticky chrome. None
   of these is used today, and all pass the CSP as-is.
3. **Perfetto is the heavy engine** — flame charts, pivots and SQL
   are never rebuilt in the page; the handoff and its query library
   grow instead (Direction 15's division of labor, restated as the
   UX growth rule).
4. **Grow the hint vocabulary, not the widget set** — a new behavior
   is usually a schema hint plus one factory branch, both guarded.
5. **Compute left, render light** — what a client library would
   compute (binning, aggregation, percentiles) belongs in Python at
   capture/serve time; the million-record density strip already
   works this way.

## The test plan

The suite is ~344 unit files, yet the defects that mattered were
found by audit rounds: the stranger walk (round 45), the user's
devtools (round 46), running the cycle twice (round 63), the
capacity sweep, the falsify ritual. Feature tests verify what was
built; only walks verify what was promised. The plan mechanizes the
walks — four rounds, ordered by escape-yield:

- **A. The journey becomes a guard** (`UX-402`): one e2e per
  journey asserting *analytic outcomes* — snapshot → analyze → view
  → handoff on example 06, cold + incremental, with the two-run
  cycle as the fixture and the answer key as the assertion.
- **B. The platform testifies** — round 46's lesson generalized:
  console errors, CSP violations, failed requests asserted zero on
  every page fixture the browser tier opens, not just the served
  page (`UX-334`'s guard already proved the class catches real
  regressions under mutation).
- **C. Populations at zero, one and many** (`UX-400`): a
  per-section parametrized sweep — empty, single-row, and the
  capacity sweep's size — catching the `UX-388`, superlative and
  `UX-367` classes generically for every future section.
- **D. The guard census** (`UX-403`): the falsify ritual run as a
  census over guard classes rather than a per-round sample; hollow
  guards fixed or deleted with the scoreboard committed.

The metric is not coverage-%: it is escaped-defect classes with no
standing detector → zero, and every future audit finding must name
the detector class that should have caught it.

## Filed

Thirteen: `UX-398` (the library question, measured against the
factory — High), `UX-399` (the browser is the library — High),
`UX-400` (populations at zero, one and many — High), `UX-401` (no
key is terminal-only in silence — Medium), `UX-402` (the journey is
a guard with an answer key — High), `UX-403` (the guard census —
Medium), `UX-404` (the unit census stops at the analyze door —
Medium), `UX-405` (a relative `--project` forfeits Plane 2 in
silence — High), `UX-406` (the spine counts every process twice in
the trace — High), `UX-407` (the finding that *is* the answer stays
at the terminal — High), `UX-408` (`serialized_pairs` described as
its own opposite — Medium), `UX-409` (the configure tax names one
payer twice — Medium), `UX-410` (a `--project` that is not a
project builds one anyway — Medium).

## Standing

Verified working on this walk, and worth recording: `bga compare`
refused the full-vs-incremental pair with the run-mode reason and
its escape hatch; `--explain` attached evidence, rule and trace
query to every claim including the refusals; the canned
`element-time` query, the page and the terminal agree on the
attribution to the digit; doctor's static census and the spine
corroborate each other ("found none among the 87 processes …
either"). Rounds 47-63 kept the audit indexes only partially — the
backlog carries every round's section, but `directions.md`'s round
history stopped at [46] and `docs/README.md`'s audits list did not
list round 63; both repaired in passing this round. The walk's
verdict sentence for the round history: the tool now finds the
answers; the remaining work is making every surface say them.
