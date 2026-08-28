# UX-369: the query library substitutes one project's element name

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-312 (the canned question library), UX-368 (findings carry their query) | **Serves:** anyone pasting a query into Perfetto | **Topic:** viewer

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
