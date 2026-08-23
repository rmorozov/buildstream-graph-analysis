# UX-231: every direction names its reader

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** the role model (`../../design/roles.md`) | **Serves:** all roles, by making their coverage visible | **Topic:** docs

## Motivation

Round 27 wrote the role model: eight roles, their interests, the
contradictions between them, and the finding that twenty-six rounds
of audits served four of them thoroughly and four almost not at all
— invisibly, because nothing required a direction or a filing to say
whose problem it solves. The gap analysis only stays true if the
tracing becomes routine.

## Required Fix

1. Directions 1-7 gain a `Serves:` line retroactively (8 and 9 were
   born with one); every future direction carries one at birth.
2. New backlog filings carry `Serves:` in their header line, with
   role ids from the role model (UX-227..234 already do; the style
   guide documents the convention).
3. The two guides state their role in their opening line
   (`real-project.md` is R1's journey; `ci-comment.md` is R4's).
4. The fixing guide's checklist gains the line: *does this change
   which roles are served, or how well? Then `roles.md`'s table
   changes in the same commit.*
5. A guard: every `## Direction N` section in `directions.md`
   contains a `Serves:` line; every task file from UX-227 up carries
   one. (Older filings are history; retro-tagging them is explicitly
   not required.)

## Out of Scope

- Retro-tagging UX-1..226 (the archaeology would be guesswork; the
  round history already tells that story).
- Any reorganisation of the backlog itself (`UX-232`).

## Acceptance Test

The guard reddens on a direction section without `Serves:` and on a
new task file without one (mutation: strip the line from Direction 8
→ red); both guides name their role; the fixing-guide checklist
carries the roles line; `grep -l "Serves:.*R6"` over the backlog
returns the R6 filings — the query the role model promised works.

## Outcome (round 28)

All five clauses landed. Directions 1–7 gained a `Serves:` line assigned
from **what each direction argues**, not from its title — Direction 4 is
"the static-binary blind spot", which reads like a capture item and is
in fact R2's, because a blind spot hides exactly the element cost R2
owns. Both guides name their role in their opening line, the fixing
guide's Definition of Done carries the question as item 7, and the style
guide documents the field as rule 10.

### The guard passed for the wrong reason, and that is the finding

The acceptance asks that `grep -l "Serves:.*R6"` over the backlog
"returns the R6 filings". Written as asked, it passed — against
**this file's own acceptance section**, which contains that exact string
inside a worked example of the query. A guard that matches the sentence
describing it is not a guard, and this one was mine, written in the same
round as UX-235's repair of three others.

Corrected, it reads only the `Serves:` field and asks about a role that
is genuinely served. The truth it then tells is the useful one:

```text
R1: 5   R2: 1   R3: 0   R4: 1
R5: 1   R6: 0   R7: 1   R8: 4
```

**No filing serves R6**, and none serves R3 either. Round 27 opened
Direction 9 for R5–R8 and filed one item, `UX-234`, which serves R5 and
R7 — the queue that R6 waits in is Direction 9's *later* work, not its
anchor. That is not a defect to fix here; it is the gap analysis doing
precisely what it was written for. The set is asserted, so the day
somebody files for R6 the guard says the map moved and `roles.md`'s
table should move with it.

**Mutations verified red and reverted:** strip `Serves:` from Direction
8 (3 guards — the acceptance's own); a new filing with no `Serves:` (1);
a `Serves:` line naming `R99`, which the role model does not define (1);
the line pushed below the fold (1); `R5` removed from `UX-234`'s line
(2, on the corrected query guard).

**Deviation from the Required Fix:** none. UX-1..226 are deliberately
not retro-tagged, as the Out of Scope section requires — the guard
starts at UX-227, where the convention starts.
