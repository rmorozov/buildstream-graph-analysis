# UX-204: buttons that know why you are going to Perfetto

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-198 (the transport this rides on), UX-194 (the questions it grows), UX-201 (the finding shapes it reads) | **Topic:** viewer

## Motivation

The external review's investigation thesis, adopted: the viewer's
job is not to render the timeline but to tell Perfetto **where to
look and why**. Today the button says "Open timeline in Perfetto" —
correct and context-free. The findings, the blast answers and the
per-element rows all know an element uid, a time neighborhood and a
question; none of it travels.

## Required Fix

1. **TraceContext, as a module not a layer**: a small link-builder
   `{element_uid?, reason, query?}` → the handoff invocation — title
   set to the reason (Perfetto shows it), and the matching canned
   query attached. What Perfetto's deep-link API verifiably supports
   is used; what it does not is not faked — the always-works floor is
   "open the trace + put the right query one paste away".
2. **Per-finding investigation buttons**: a finding with elements
   gains `Investigate in Perfetto` carrying its context; blast
   answers and the top rows of element tables the same.
3. **The questions grow into a library**: the five canned queries
   become a categorized page (scheduling / execution / dependencies /
   resources), each with its one-sentence what-it-answers; findings
   reference queries by id so the button and the page cannot drift.
   The exported report inlines the library (UX-199 item 4 does the
   inlining; this item fills it).

## Out of Scope

- Rendering query results in our page (Perfetto's job).
- Any timeline drawing.

## Acceptance Test

The harness: a finding's investigate button produces a handoff whose
title names the finding and whose attached query is the library
entry its id references (mutation: detaching the id linkage
reddens); a run with no timeline renders no investigate buttons
(dead-button rule); the library page lists every query the findings
reference (coverage asserted both directions); queries still parse
under `trace_processor_shell` where installed (the UX-194 marked
test, extended).

## Outcome

All three parts, and the drift the third one closed was real rather
than hypothetical.

**1. `trace_context.js`, a module not a layer.** Every function in it is
a pure function of data the page already has: nothing fetches, nothing
renders. `traceContext({element_uid, reason, query})` returns the
handoff invocation — `title` is the reason (Perfetto shows it in the
tab, so a reader with three open can tell them apart) and `sql` is the
library entry with the element substituted.

**What is deliberately not built:** the query is not smuggled into the
deep link. Perfetto's documented deep-link API takes a trace and a
title; there is no supported way to preload the Query pane, and faking
one would be a feature that breaks on their next release. The
always-works floor is what shipped: open the trace, and put the right
query one paste away. The paste appears on click *whether the handoff
succeeds or not* — a blocked pop-up is exactly when the reader needs
the SQL most.

**2. Per-finding buttons, under the dead-button rule.** `renderFindings`
takes the investigator as an argument and `boot()` passes it only when
`run.has_timeline`. No timeline, no buttons — `UX-194`'s rule, applied
to ten more buttons than it was written for. Ten finding ids map to
queries; a finding no query answers (`confidence`) gets no button
rather than a button that opens the trace with nothing.

**3. The library — and the copy it turned out to be hiding.** The five
questions gained ids and categories, plus a sixth so `dependencies` has
one. `sql.html` **rendered its own hand-written copy of every query**:
the only guard on the two agreeing compared *titles*, so any change to
a query's SQL would have drifted silently, and the SQL parse tests were
checking the copy rather than the source. The page renders
`questions.js` now, the tests read the module, and the single-source
guard asserts there is nothing left to drift from — `sql.html` may not
contain a `<pre><code>` block at all.

Coverage is asserted **both directions**: every query a finding
references is on the page, and every question on the page is reachable
from some finding (a question nobody's report links to is a question
nobody finds).

**A real bug the falsification pass caught.** `hidden` set through
`el()` lands as a *property* — `el` assigns non-`data-` attributes that
way — so the click handler's `removeAttribute("hidden")` cleared
nothing and the paste would never have appeared in a browser either.
The first version of the reveal guard did not catch it: the probe asked
whether `hidden` was in the shim's attribute bag, where it had never
been, so the assertion passed vacuously. Both are fixed — the property
is cleared as a property, and the probe reads the property.

Tests: 13 new, plus three rewritten to read the module instead of the
page. Seven mutations, each red, including the acceptance's named one
(detaching the id linkage) and the reveal mutation that exposed the
vacuous guard above.

**The page-size guard measured the wrong bytes.** `< 80,000 B` summed
every file in `bga/viewer/`, which counts `sql.html` and
`perfetto.html` — two served-only pages an export never carries. This
round crossed that number while the exported page was still comfortably
under it. It measures the exported file with its `application/json`
blocks removed now, which is what Direction 7's rule is about. Measured
on the real `examples/06` export: **72,520 B of page against 71,052 B
of data** — worth recording, because the ratio the original docstring
claimed (816,573 vs 39,119) does not hold for a small capture, and the
guard is now honest about which number it is watching.
