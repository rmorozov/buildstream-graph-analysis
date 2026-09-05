# UX-337: the two viewer modules split along their seams

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-336 (which measured the cost and deferred this), UX-199 (the export's derived module order), UX-294 (the module map) | **Serves:** the maintainers — edit cost, not page cost | **Topic:** guards | **Area:** bga/viewer

## Motivation

`UX-336`'s fifth lever, split out of it rather than rushed inside it.
The two largest viewer modules are long enough that every edit pays a
long read:

```text
bga/viewer/app.js     2,614 lines
bga/viewer/views.js   2,484 lines
                      -----
                      5,098 of the viewer's 9,603
```

`views.js` already carries its chapter seams as comment rules — band,
trend, blast box, overview, the two graphs, the decision, the element
object — so *where* to cut is not the open question.

**What is.** The export inlines modules by concatenating them in
dependency order (`tools/bga_view.py::_module_order` walks `import`
lines; `_inline_module` strips `export ` and blanks the imports). Two
consequences the split has to respect and `UX-336` did not have room to
establish:

- the order must be **acyclic**. A chapter that both calls into and is
  called from what stays in `views.js` would produce a cycle, and the
  inliner's whole premise is "what it imported is now declared above
  it";
- `export * from` and bare `export { a, b };` re-export forms are
  invisible to `_module_order` and survive `_inline_module` verbatim —
  so the tidy "keep `views.js` as an index" shape does not work, and
  the two importers (`app.js`, `nav.js`) have to name the new modules.

`UX-199` is on file because exactly this inlining shipped an export
that threw `ReferenceError` in `boot()` and rendered **empty** for
several rounds. That is the risk this item is about.

## Required Fix

The dependency graph between the chapters is derived (not guessed)
before anything moves; the two files split along seams the graph shows
are acyclic; `app.js` and `nav.js` import the new modules directly.
Page cost stays neutral — the export inlines either way — and the
export's byte size is asserted before and after. `UX-294`'s module map
gains the new files in the same commit.

## Out of Scope

- Changing any rendering behaviour. This is a move, and the diff should
  read as one.
- Splitting anything else in `bga/viewer/`. The other five modules are
  486 lines and under.

## Acceptance Test

No file in `bga/viewer/` over 1,500 lines; the exported page boots
under the DOM shim and renders the same section list as before (asserted
against a before/after capture, not a literal); the export's byte size
moves by less than 1%; `_module_order` returns an acyclic order
containing every new module (asserted); the module map names them.

## Groundwork (round 50) — the graph, derived

Not closed this round, and deliberately not started: this is a pure
move with no user-visible change, and its own Motivation names the
risk — `UX-199` is on file because exactly this inlining shipped an
export that threw `ReferenceError` in `boot()` and rendered **empty**
for several rounds. Landing it inside a batch of three unrelated fixes
would make the one diff that has to read as a move read as a rewrite.

What *was* done is the part the Required Fix says must come first —
**the dependency graph between the chapters, derived rather than
guessed** — because it turned up something that changes the shape of
the work:

```text
chapter                               lines  defines  depends on
(preamble)                               54        4  -
band                                    198        5  (preamble)
trend                                   197        3  (preamble), band
blast box                                97        3  UX-206: two graphs
UX-202: the overview                    264        7  (preamble), UX-206: two graphs
UX-206: two graphs                      180        6  (preamble), the element object
UX-207: the decision                    548       11  (preamble), the element object
the element object                      993       25  (preamble), UX-202: the overview, band
```

**The chapters are not acyclic.** There is a three-chapter cycle:

```text
UX-202: the overview  ->  UX-206: two graphs  ->  the element object
                      <-------------------------------------------
```

and it is created by exactly three symbols, one per edge:

```text
UX-202: the overview  ->  UX-206: two graphs   OVERVIEW_SHOWN
UX-206: two graphs    ->  the element object   elementAnchor
the element object    ->  UX-202: the overview  bar
```

All three are **primitives, not chapter content**: a constant (`4`), a
pure string function, and a DOM row builder. None of them belongs to
the chapter it happens to sit in, and the cycle is entirely an artifact
of where they were written down.

So the split has a step the filing did not know it needed, and it comes
first: a shared module for the primitives (`svg`, `seconds`, `mib`
already live in the preamble and belong with them), after which the
seven chapters *are* acyclic and the inliner's premise holds.

The rest of the shape, measured:

```text
bga/viewer/views.js   2,531  ->  element object (993) out, primitives out  ~1,478
bga/viewer/app.js     2,752  ->  table machinery (~1,150) and format (~160) out  ~1,440
```

`app.js` has only three comment seams (`format`, `render`, `boot`) and
the middle one is 1,956 lines, so its cut is by *function group* rather
than by an existing rule: the table machinery from `columnSpecs` to
`renderPairs` is one contiguous block and one subject.

## Outcome (round 51, 2026-08-27) — 🟢 Done

### The gap, measured

```text
bga/viewer/app.js     2,752 lines
bga/viewer/views.js   2,531 lines
                      -----
                      5,283 of the viewer's 9,603
```

### After

```text
bga/viewer/views.js         941    bga/viewer/primitives.js    114
bga/viewer/app.js         1,210    bga/viewer/format.js        231
                                   bga/viewer/structured.js  1,357
                                   bga/viewer/element.js     1,013
                                   bga/viewer/decision.js      571

exported page, both committed fixtures, booted in real Chrome:
golden       28 sections -> 28  identical=True  330,515 B -> 330,517 (+0.00%)
macro_micro  40 sections -> 40  identical=True  369,957 B -> 369,959 (+0.00%)
failed sections: []   pageFailed: False

_module_order(), 20 modules, dependency order:
primitives format controls drawings shapes tablefocus tables views
structured perfetto element decision chapters nav rawjson focus
viewstate questions trace_context app
```

The two bytes are the `?.` added to `app.js`'s boot guard.

### The cut is derived, and the deriving is the work

The Required Fix says the graph comes first, and it earned its place
twice.

**Once in the filing** (round 50's groundwork): the seven chapters of
`views.js` were *not* acyclic, and the cycle was three edges of one
symbol each — `OVERVIEW_SHOWN`, `elementAnchor`, `bar`. None is chapter
content. `primitives.js` took them and the chapters became a DAG.

**Once again here**, on `app.js`, which has no comment seams to cut
along in its middle 1,956 lines. The symbols crossing each candidate
group were counted before anything moved:

```text
app        <- format     COLUMNS DISTRIBUTION QUANTITY SERIES SEVERITY
                         bytes childNode cssId el guessQuantity heading
                         hintsOf quantity quantityFor sectionHead title
app        <- primitives safeStorage served
app        <- structured ARRAY_INLINE_ITEMS CELL_NEST_LIMIT
                         OBJECT_INLINE_FIELDS describedTerm
                         liftedCriticalPath renderPairs renderStructured
                         renderTable
structured <- format     ... + DIRECTION PRESETS QUESTION elementColumn
structured <- primitives safeStorage served
structured <- app        render        <- a parameter, not a call
```

The first run of that count used regexes to strip comments and strings.
It reported a *cleaner* split than the real one — no `PRESETS`, no
`elementColumn`, no `safeStorage` — because the template-literal
pattern, written to skip `${…}`, failed to match any template that had
one and paired its backtick with a later one, eating 90% of the file:

```text
app.js blocks, raw          1,124 lines
after block comments        1,024
after line comments         1,024
after template literals       148     <- here
```

The numbers above are from a character scanner that knows a `//` inside
a string is not a comment. Trusting the first count would have shipped
three `ReferenceError`s.

### What the guard asserts, and why those clauses

`_module_order`'s `walk()` adds a module to `seen` **before** recursing,
so a cycle does not hang: it emits an order in which a module precedes
something it imports, the concatenated blob reads a `const` in its
temporal dead zone, and the page is empty — `UX-199` by a new route.
Mutation A2 shows exactly that, with `format.js` landing *after*
`structured.js` in an order that was still produced without complaint.

Nothing asserted that before. Nothing asserted the re-export blindness
either, and "keep `views.js` as an index" is the tidy shape a future
round will reach for.

### Tests reach the viewer, not a file

36 test files imported `app.js` or `views.js` for a symbol. Re-pointing
each by hand would make a pure move read as a rewrite, and would do so
again at the next move, so `tests/viewer.mjs` re-exports the modules the
export inlines and the snippets name that. `bga/viewer/` itself still
may not re-export, which the guard asserts; no two of the 20 modules
export the same name, so `export *` drops nothing.

Six Python source scans read `bga/viewer/app.js` or `views.js` as
*text*. Those now read the modules the text moved to, each with the
reason in place — `test_the_page_opens_the_way_it_says` was the
instructive one: against `views.js` alone its census would have reported
`renderWhyRanked` as an entry for nothing.

### Mutations verified red and reverted (6)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| A1 | the `views.js`/`element.js` split undone — `element.js` concatenated back (1,954 lines) | `test_every_viewer_module_is_under_the_ceiling`, and `test_every_module_comes_after_everything_it_imports` (the concatenation carries `element.js`'s own `import … from "./views.js"`, so `views.js` imports itself) — 2 failed, 47 passed |
| A2 | a cycle: `format.js` imports `renderTable` from `structured.js` | `test_every_module_comes_after_everything_it_imports` — 1 failed, 48 passed. The order was still produced: `… views structured format perfetto …` |
| A3 | `views.js` keeps the chapters as an index: `export * from "./element.js";` | `test_the_module_re_exports_nothing[views.js]` — 1 failed, 48 passed |
| A4 | `structured.js` dropped from `ASSETS` — inlined but not served | `test_everything_inlined_is_also_served` — 1 failed, 48 passed |
| A5 | `app.js` imports `./structured2.js` | `test_every_import_names_a_module_that_exists[app.js]` and four others — 5 failed, 44 passed |
| A6 | `_module_order` returns `order[1:]` | `test_the_order_reaches_every_module_app_js_depends_on` and `test_every_module_comes_after_everything_it_imports` — 2 failed, 47 passed |

A6 is the one that shows the reachability clause carries its own weight:
A2, A3 and A4 all leave it green.

### Deviation from the Required Fix

- `app.js` also grew one `?.`: its single top-level statement,
  `document.getElementById("report")`, throws at *import* under a shim
  that provides only what its own assertions need — and every test now
  reaches the formatters through a namespace that includes `app.js`.
  A throw there takes the whole test with it rather than one assertion,
  which is the reason `served()` is already guarded and says so. Two
  bytes on the exported page.
- The Required Fix names `app.js` and `nav.js` as the importers of the
  new modules. `nav.js` imports `primitives.js`; `app.js` imports
  `primitives.js`, `format.js` and `structured.js`. `element.js` and
  `decision.js` are imported by `app.js` too, and `structured.js`
  imports `views.js` for `PATH_HEAD`/`PATH_TAIL` — one more edge than
  the filing anticipated, and it points down.
- `renderBlastTree` was in `app.js`'s import list and used nowhere;
  `views.js` draws the tree inside `renderBlastSearch`. Dropped, with
  the reason in place.
