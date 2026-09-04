# UX-650: nine page-built sections declare no reader

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-643 (which built the mechanism and could not reach these) | **Found by:** round 88, by track Q naming what its brief forbade it to touch | **Serves:** the reader whose role owns a section the page builds rather than the payload | **Topic:** viewer

## Motivation

`UX-643` gave the page a reader role that demotes. Eleven payload
sections carry one, **derived** rather than authored — the join of
`provenance._CLAIMS`' evidence paths with `findings.FINDING_READERS`.

Nine sections are built by the page rather than published by the
payload, and so are not in that join and declare nothing:

```text
views.js       blast · overview · evidence · critical-path-drawn
element.js     whatif · horizon · culprits
questions.js   perfetto-questions
```

`UX-643`'s Required Fix names them — "the ~9 page-built sections
naming theirs at the call site" — and they were not delivered. The
reason is worth recording because it was not a judgement about the
sections: round 88's track brief gave `views.js`, `element.js` and
`questions.js` to no owner, so the track that held the mechanism was
forbidden the three files that needed it. The task was narrowed by the
work order, not by the code.

The consequence is small and bounded, because the design already
handles an unmapped section: all nine stay folded under every role and
are reachable under all of them. But `blast` is the section a
capacity-and-impact reader would most want promoted, and it is exactly
the one that cannot be.

## Required Fix

Each of the nine names its reader at its construction site, in the
same vocabulary the payload sections use. The role is **argued from
what the section answers**, not guessed to fill the table: a section
whose reader cannot be established from the code stays unmapped, which
is what `UX-643` did with `decision`, `readers`, `findings`, `summary`
and `next_steps` and is a legitimate outcome here too.

`UX-643`'s guard extends to the page-built population rather than
being duplicated: it currently recomputes the payload join, and the
call-site declarations are a second source it must read the same way.

## Out of Scope

- The five payload sections `UX-643` left unmapped — declined because
  they are indexes over *all* findings or over the run's identity, so
  "which reader" has no answer the code gives, and that reasoning does
  not change here.
- The five findings that contribute nothing to the join
  (`graph-width`, `memory-envelope`, `wait-category`, and the two
  blast-radius findings) — declined because two publish an empty path
  tuple and three compute their paths from the document, so the fix is
  in how those findings declare evidence, not in this row.

## Acceptance Test

On both fixtures, every page-built section either declares a reader or
is deliberately unmapped with the reason at the site; the sections that
declare one are promoted under that role and folded under the others;
nothing is removed from the DOM under any role.

## Outcome (round 88, 2026-09-04) — 🟢 Done

**The nine are thirteen.** The list this row was filed with came from a
report; `grep -n 'data-section", "\|"data-section": "' bga/viewer/{views,element,questions}.js`
finds four more construction sites — `band`, `store-trend` and
`blast-tree` in `views.js`, and `element.js`'s one-per-element block.
Nine declare a reader, four are unmapped with the reason at the site:

```text
views.js     blast (search + offline)  R2    overview             unmapped
             blast-tree                R2    element.js
             evidence                  R4      element-<uid>      unmapped
             critical-path-drawn       R1      culprits           unmapped
             band, store-trend         R4    questions.js
element.js   whatif, horizon           R1      perfetto-questions unmapped
```

**Two are derived, not argued.** `whatif` and `horizon` *are*
`payload.optimization_horizon`, and that key joins to R1 in
`schemas._SECTION_READERS`. `evidence` renders `confidence.*`, where
four of the five findings are `ci-gatekeeper` and the fifth is the
failed-build one — R4, whose question is this section's heading.
`blast` is R2 on the two findings the join could not reach:
`blast-radius-reach` and `blast-radius-structural` are `recipe-author`
and compute their paths from the document, and `resource_blast` beside
it in the same chapter joins to R2. `band` and `store-trend` are R4 on
`verdict_kind`, the field `_compare_exit_code` gates on.
`critical-path-drawn` is the one argued from the drawing alone — every
box carries its `realizable_saving_us` — because no finding cites
`critical_path_detail`.

**Four refused.** `overview` is the run's whole duration in twelve
published buckets, the index shape `UX-643` refused for `summary`;
`perfetto-questions` is seventeen queries spanning all five roles;
`culprits` renders `element_deltas.rows`, which no verdict and no
finding reads; and an element block cannot know which element is the
reader's, so declaring R2 would promote eleven at once. All four stay
folded under every role and reachable under all — the designed
behaviour, and `UX-643`'s reachability clause still finds one.

**The contract holds, measured either side on both fixtures:**

```text
                     promoted R1/R2/R3/R4/R5   landed   under a role
golden    before          6 1 2 2 -             2,834      2,838
          after           9 2 2 3 -             2,839      2,843
macro     before          6 2 2 3 1             5,469      5,473
          after           9 3 2 4 1             5,474      5,478
```

Section text byte-identical under all five roles and at "anyone" on
both, before and after; the section list identical; the node count
moves only up, by `UX-372`'s four, and returns exactly at "anyone".
The five landed nodes added are the five tags, one per page-built
section that declares and renders. `test_the_page_has_a_volume_budget`
passes: 5,474 nodes against the 7,900 the 11-element class bounds.

**The export grew 609 B on both, all source** — comments are stripped
by `_uncommented`, so the arguments at the sites cost nothing:

```text
golden       428,015 -> 428,624 B   bound 432,000, 3,376 B left
macro_micro  478,520 -> 479,129 B   bound 482,000, 2,871 B left
```

No bound moved. `dev_js_deps.py --order` is unchanged and acyclic:
`declareReaders` lives in `views.js`, which already inlines above
`element.js`.

**Mutations verified red and reverted (5):** the unmapped marker
removed from `renderQuestions` — a site that neither declares nor says
why; `renderHorizon` declaring `R6`, a role the roster does not have;
`declareReaders` building the tag and never appending it — a
declaration that does not reach the DOM; `renderOverview` declaring R1
against its own refusal; and `renderQuestions` rewritten as a `const`
so the seam parse loses the site, which is the clause that keeps the
parse from passing on nothing.

**Deviation:** none of the nine were declined for the reason the row
predicted — `blast` is mapped. The count was wrong instead.
