# UX-650: nine page-built sections declare no reader

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-643 (which built the mechanism and could not reach these) | **Found by:** round 88, by track Q naming what its brief forbade it to touch | **Serves:** the reader whose role owns a section the page builds rather than the payload | **Topic:** viewer

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
