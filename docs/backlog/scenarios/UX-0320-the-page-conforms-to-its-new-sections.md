# UX-320: the page conforms to its new sections

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-316, UX-317, UX-318, UX-319 (the mechanisms), styleguide §2a/§2b/§3a/§3b | **Serves:** R1; the maintainers | **Topic:** viewer

## Motivation

Round 44 extended the visual contract with four sections earned by
field complaints; the UX-305 precedent says an extension is not
real until the existing page is audited against it and the audit
is a guard. This task is that pass: every drawing graded, every
fold counted, every control's apparatus with its control, every
chapter within budget — and the conformance walks joined to the
suite so the next section ships conforming or amends the guide.

## Required Fix

The conformance pass over the whole page against §2a/§2b/§3a/§3b,
with demotions/moves listed in this file's log (the UX-305 shape);
the walks join `test_the_mapping_is_law.py`'s family: grade walk
(every drawing annotation or exhibit, geometry from the scale),
apparatus walk (no control explained from another block; header
budget), depth walk (every fold counted; no nested scrollboxes),
click walk (§3b's budget). The fixing guide's checklist line
extends to the new sections.

## Out of Scope

- New mechanisms (they live in UX-316..319; this is conformance
  and enforcement).

## Acceptance Test

All four walks green on both pages at two viewports; each walk
proven discriminating by one mutation (a mis-graded drawing, a
header prose line, an uncounted fold, a third-click path — each
red); the pass's changes listed in the log; the fixing-guide line
present.

## Log

The `UX-305` shape: the pass, what it moved, and the walks that keep it.

**What the pass found.** Every drawing, every fold, every control and
every section on both committed exports, against §2a/§2b/§3a/§3b:

```text
every <svg> in main            graded, box from the scale          ok
every value fold               levels + rows                        ok
`evidence-detail`              "The numbers behind that", no count  FIXED
`question-group`               "scheduling (3)" - counted already   ok
`provenance` / `why-ranked`    one prose block each                 declared
`long-text`                    the rest of a string, shown          declared
header                         3 blocks, 0 controls                 ok
sections in the rail           28/28 and 37/37                      ok
sections opening collapsed     0                                    ok
scroll containers nested       0                                    ok
```

**One demotion, and it is the pass's whole justification.**
`evidence-detail` folds *published values* — the numbers behind the
verdict — and is built by hand in `views.js`, outside the renderer
`UX-318` taught to count. Four per-item guards passed and this one
surface said nothing about its depth. It says "1 level, N rows" now.

**One line drawn, deliberately.** §3a.1's subject is "a cell that folds
deeper content". `provenance`, `why-ranked`, `long-text` and
`question-group` fold something else — one prose block, or the rest of
a string, or a group that already counts itself — so they are
**declared** in `LAYOUT_FOLDS` with the reason, and a second clause
asserts each declared name is still built by some module, so an
exemption cannot outlive its fold and quietly cover the next thing to
take the name.

**A claim this pass falsified.** Round 41's page-budget note said "the
export inlines every module verbatim, comments included ... 175 KB of
the 196 KB page is commented JavaScript", and the ratio guard was
lowered from 4x to 3.5x on that reasoning. It is not true:
`_uncommented` in `tools/bga_view.py` has stripped whole-line and block
comments from the inlined copy since `UX-205`. Measured:

```text
page     223,276 B
  js     198,058 B   89%   trailing `//` on code lines ~114 B
  css     22,247 B   10%
  rest     2,971 B
data     764,900 B   3.43x
```

The page is **code**. `UX-307`'s remaining scope is those ~114 bytes
plus whatever a minifier would buy — which its own Required Fix
declines — so its motivation is corrected in its file rather than its
status changed. The ratio moves to 3.3x with the true reason recorded:
the viewer grows features while the synthetic run's data does not grow
with it, and a round that wants the page smaller should decide whether
this ratio is the right instrument at all.

**The page budget, with its ledger.** +44,601 B of checked-in viewer
source this round, none of it data:

```text
app.js        104,875 -> 118,215  (+13,340)  grades, folds, focus, ?
drawings.js    12,545 ->  21,421   (+8,876)  the scale, twin, tick row
style.css      34,575 ->  43,052   (+8,477)  §2a/§2b/§3a's rules
tablefocus.js       0 ->   6,692   (+6,692)  table focus, a new module
views.js       98,792 -> 102,947   (+4,155)  the graded figures
shapes.js       6,541 ->   8,082   (+1,541)  shapeOf
index.html      2,160 ->   3,103     (+943)  the actions group
viewstate.js   10,686 ->  11,263     (+577)  tf= in the fragment
```

`PAGE_BUDGET_B` 210,000 → 226,000; golden 308,000 → 324,000;
macro_micro 348,000 → 364,000. The two guards that can tell a feature
from a library — *the page is the modules and nothing else*, *no module
looks like a vendored library* — both stayed green throughout, which is
the condition that file's own backstop sets for raising rather than
trimming.

**The fixing guide's checklist** now asks the four new questions and
names the guard that answers each, and a clause here holds it to that:
a section nobody is told to check is a section that decays.
