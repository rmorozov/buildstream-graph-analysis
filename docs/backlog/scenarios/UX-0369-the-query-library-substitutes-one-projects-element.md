# UX-369: the query library substitutes one project's element name

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-312 (the canned question library), UX-368 (findings carry their query) | **Serves:** anyone pasting a query into Perfetto | **Topic:** viewer | **Area:** bga/viewer

## Motivation

Thirteen queries ship. Three of them ask about **one** element:

```text
element-commands   "What did one element actually execute?"
dependency-wait    "What was this element waiting for?"
waited-on-flow     "What did this element wait for, by the graph?"
```

Each carries a `{element}` placeholder, and the page fills it:

```javascript
export function renderedSql(question) {
  return question.sql.split("{element}").join(question.example ?? "");
}
```

`question.example` is the literal `"core.bst"`, three times, in
`bga/viewer/questions.js`. `core.bst` is a real element — **of
`macro_micro`**. It is one fixture's element name compiled into a
library shipped for every project.

So a reader on any other build copies a query, pastes it into Perfetto
and gets zero rows, with nothing on the page saying which token to
change. The page knows this run's elements — the element table draws
them, `headline.top_actions` names three — and the substitution reads
none of them.

There is no substitution mechanism at all: `questions.js` contains no
occurrence of `param`, and `{element}` is the only placeholder.

## Required Fix

The substituted value comes from **this run**, and the reader can change
it.

- Default to an element the run actually has, and the obvious default is
  the one the page is already pointing at — `headline.top_actions[0]`,
  which is `core.bst` on `macro_micro` and something else everywhere
  else. The literal becomes correct on one fixture by coincidence
  instead of by hard-coding, which is the point.
- A control that swaps it, over the run's own element list, re-rendering
  the SQL and the copy button with it. This is the "query builder" the
  round asked for at its smallest honest size: one substitution, over a
  population the page already holds.
- The placeholder is visible when unfilled, so a reader can see there is
  a value to choose rather than inferring it from zero rows.

## Falsification

Export a page from a run that does **not** contain the hard-coded name
and assert no rendered SQL contains it — `tests/fixtures/with_timeline`
and the synthetic scale run both qualify. It fails today: `core.bst`
appears in three queries on every page the tool writes.

Then the substitution half: change the control and assert the rendered
SQL *and* the copy button's payload both move. A builder that updates
the display and copies the old text is worse than none.

## Out of Scope

A general SQL editor. Perfetto has one, it is where the reader is going,
and `UX-296` is why this page does not parse SQL. The scope here is the
values the page already knows being filled into the queries it already
ships.

## Outcome (round 59, 2026-08-28) — 🟢 Done

### The gap, measured

The seeded 1,202-element run, whose elements are all called
`layer08/mod099.bst`, exported before the fix:

```text
$ bga gen-synthetic /tmp/scale --seed 1
$ bga view /tmp/scale --export /tmp/scale.html
$ grep -o 'core\.bst' /tmp/scale.html | wc -l
3
```

Three — one per element-scoped query, none of them an element of that
run. `golden`, whose elements are `base/extra/lib/app.bst`, said it
three times too.

### After

```text
$ grep -o 'core\.bst' /tmp/scale.html | wc -l
0
```

and, measured in Chromium on that page:

```text
options offered                   1202
note beside the control           "3 of the queries below ask about one
                                   element. All 1202 of this run's
                                   elements are here; the default is the
                                   one the report's first action names."
default (golden)                  base.bst      == headline.top_actions[0]
default (macro_micro)             core.bst      == headline.top_actions[0]
after selecting the last option   SQL and data-copy both moved, equal
```

`macro_micro` still renders `core.bst` — by coincidence now rather than
by compilation, which is the whole shape of the fix.

### The substitution reads the run, and the reader can change it

`renderedSql(question, element)` takes the element; `QUESTIONS` carries
no `example`. `renderQuestions` is given `elements` and `element` by
`app.js` and draws one `<select>` over the run's own population, and
`applyElement` re-renders every `[data-sql-for]` node — the `<code>` a
reader reads and the `data-copy` a reader pastes, from one call. With
no run behind the page (`sql.html`), there is no control, the token
`{element}` stays visible, and a sentence says what to put there.

**Two corrections the measurement forced, both mine.**

`elementUids` first read `elementFacts`, which is built from the
published top-N arrays: 26 options on a 1,202-element run, beside a
sentence saying "26 in this run". That is `UX-366`'s defect committed
again one control over. It reads `elements.element_durations` now, with
the facts map unioned in.

The label was written `make("label", { for: "query-element" })`, and
`format.js`'s `el` assigns any name without a hyphen as a **property** —
a label's reflecting property is `htmlFor`, so the attribute landed
nowhere. Chromium reported `FormLabelHasNeitherForNorNestedInput` and
`test_the_console_stays_clean.py` failed on the golden export. It uses
`controls.js`'s `labelFor` now, which is the seam every other labelled
control in the viewer already goes through. This is `UX-317`'s defect
one property over, and the `el` factory can still do it to the next
caller.

### Mutations verified red and reverted (5)

Counts are what the run printed, not what was expected of it. Run
against the committed tree, after `e902b8f` — twice before, a sweep
over uncommitted edits wiped work in progress and produced errors that
looked like caught mutations.

| # | mutation | reddened |
|---|---|---|
| M1 | `example: "core.bst"` back on the three entries | 4 failed, 6 passed — `test_no_entry_carries_a_hard_coded_example`, `test_an_unfilled_query_shows_the_token`, `test_no_query_on_the_page_names_another_projects_element`, `test_the_picker_offers_the_whole_run` |
| M2 | `renderedSql` falls back to `""` rather than the token | 1 failed, 9 passed — `test_an_unfilled_query_shows_the_token` |
| M3 | `applyElement` updates `textContent` and not `data-copy` | 1 failed, 9 passed — `test_changing_it_moves_the_query_and_the_paste_together` |
| M4 | `elementUids` reads `elementFacts` alone again | 2 failed, 8 passed — `test_it_reaches_an_element_no_published_array_names`, `test_the_picker_offers_the_whole_run` |
| M5 | `copyButton` copies its closure text, not `data-copy` | **0 failed at first** — the guard read the attribute the fix sets rather than the thing the reader receives. A clause that stubs the clipboard and presses the control was added; the mutation now gives 1 failed, 9 passed — `test_pressing_copy_hands_over_the_query_now_on_screen` |

M5 is the one worth keeping: nine clauses passed over a build whose
`data-copy` was correct and whose clipboard was stale, which is the
exact failure the `Falsification` section calls worse than no builder
at all. The sweep found the hole rather than confirming the guard.

### Deviation from the Required Fix

- **The falsifying capture named in the filing does not falsify.**
  `Falsification` proposed `tests/fixtures/with_timeline`; that capture
  has an element *called* `core.bst` (40 occurrences on its page), so it
  cannot tell the substitution from the coincidence. `golden` can, is
  already committed, and is what the page-level clauses run on. The
  synthetic run is kept for the one claim only scale can make.
- Otherwise none.

### One thing this moved that belongs to another item

The export's `data > 2.6 × page` bound is at **2.6008** with this
change in — about 200 B of headroom on a 263,509 B page. That guard's
own comment says a third restatement would make it a record of the
page's growth rather than a bound on it, so it was not restated and the
feature was fitted under it instead. The next viewer item that adds a
control will not fit. Recorded in `UX-367`.
