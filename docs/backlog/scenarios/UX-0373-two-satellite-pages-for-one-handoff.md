# UX-373: two satellite pages for one handoff

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-281 (the satellite pages are dead ends), UX-199 (a report you can find your way around), UX-369 (the substitution) | **Serves:** anyone following the handoff out of the report | **Topic:** viewer

## Motivation

The viewer ships three pages:

```text
bga/viewer/index.html      3,096 B   "bga report"
bga/viewer/perfetto.html   2,326 B   "bga → Perfetto"
bga/viewer/sql.html        2,010 B   "bga → PerfettoSQL"
```

Two of them are the same errand split in half: how to open the trace,
and what to ask it once open. A reader who presses the button needs both
in the order they need them, and `UX-199`'s own complaint was that this
report is hard to find your way around.

The export already knows they belong together — it **inlines the SQL
page's section into the report** and strips the link, because `UX-199`
found the export dropping the link and leaving nothing behind it. So the
one-page arrangement already exists and only the served path is split.

The round proposed merging them and putting a query builder in the
merged page. The builder is `UX-369`; this is the surface it would live
on, and the two decisions are separable — which is why this is Low and
that is Medium.

## Required Fix

One `perfetto.html`: what the handoff is, how to open it, then the
library, then the substitution control `UX-369` adds. `sql.html` keeps
its URL as a redirect rather than a dead link — the store and older
exports point at it.

The served and exported arrangements should then be the same shape,
which is the property the export's inlining already reaches for.

## Falsification

Every link the report draws to a satellite page resolves to a page that
exists and carries the section it promises. Then: the served page and
the exported section render the same query library from the same module
— which they do today (`UX-199`), and a merge must not be the thing that
splits them.

## Out of Scope

`index.html`. The report is the report; this is about the two pages
behind the handoff.

## Outcome

Round 59. One page behind the button.

**The merge.** `perfetto.html` carries the query library under the
handoff, rendered by `perfetto_page.js` from `questions.js` — the same
module `app.js` inlines into the export, so `UX-204`'s single source
survives the operation most likely to break it. `sql.js` was fourteen
lines and is now that function; the list has one renderer again.

**And the run came with it, which the filing only implied.** `sql.html`
had no documents beside it, so `UX-369`'s element control had no
population and every element-scoped query showed the bare `{element}`
token. The merged page is served next to `report.json` and `run.json`,
so it reads the same three facts `app.js` passes — whether there is a
timeline, which planes are in it, and this project's own element uids.
Measured on `macro_micro`, served:

```text
handoff button      present
questions           13, in 4 category folds
element picker      11 options, defaulting to core.bst
console             clean; no CSP violations
```

That is the Required Fix's third element built rather than described:
the substitution control is on the merged page.

**`sql.html` stays.** A `<meta http-equiv="refresh">` redirect with a
visible link under it. The URL is published — the store's older exports
point at it, and so does anything pasted into an issue — and `UX-281`'s
rule is that a satellite page is not a dead end. Not a script redirect:
this page's own `default-src 'self'` refuses inline script, which is
exactly how it rendered nothing before `UX-266`.

The Falsification's second clause held throughout and was not touched:
the served page and the exported section render the same library from
the same module.

### What the merge made visible

Served on `macro_micro`, the merged page said two things at once:

```text
top of page      [Open in Perfetto]
one section down "This snapshot carries no build log, so there is no
                  timeline to open here"
```

Both true of the page, one true of the run. `index.html` has gated its
own button on `run.has_timeline` since `UX-194`; the standalone handoff
page never had, and nothing on it contradicted the button until the
questions moved in. So the gate is here now, and the page says what to
run instead of leaving a blank where the button was (`UX-321`).

**The library is not gated.** A reader deciding whether to capture a
trace is exactly the reader who wants to know what they could ask it.

### A guard fixed on the way

`test_every_page_script_is_served` sliced `ASSETS` at the first `)`.
The tuple's own prose is prose, and a comment added this round
contained a parenthesis — which truncated the slice a third of the way
in and reported six served modules as missing from a list that has
them. It slices to the closing line now and asserts it read the whole
tuple, so the next parenthesis fails nothing and the next real omission
still does.

### Falsification run

Six mutations against the committed tree, all caught:

| # | Mutation | Caught by |
| --- | --- | --- |
| M1 | `sql.html` dead-ends — the deletion this item did not do | `test_it_names_where_the_content_went`, `test_it_redirects_without_script` |
| M2 | a query title written out in the markup again | `test_nothing_writes_a_query_out_by_hand` |
| M3 | the dead-button gate removed | `test_a_run_without_one_does_not`, `test_the_absence_is_said_and_not_just_shown` |
| M4 | the library gated on the timeline too | `test_the_questions_are_still_there_without_a_timeline` |
| M5 | the page renders the library without reading the run | `test_the_substitution_control_is_here`, `test_the_queries_name_the_chosen_element` |
| M6 | the report links the old page | `test_the_report_points_at_the_merged_page` |

M5 first failed with a `TypeError` rather than a sentence — `None in
str` — so the clause names its precondition before using it. A guard
that discriminates and cannot say why is half an instrument.
