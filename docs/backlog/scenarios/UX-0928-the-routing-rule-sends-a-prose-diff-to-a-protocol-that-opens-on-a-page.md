# UX-928: the routing rule sends a prose diff to a protocol that opens on a served page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-701, UX-664, UX-727 | **Blocks:** — | **Found by:** round 136 — `UX-924`'s diff routed to `design-review` for one paragraph added to `.claude/skills/verify/SKILL.md`, and touched no page at all | **Serves:** every diff that edits a skill, a hook or the spec without touching the report | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-701` put the routing rule in code so a guard can run it:

```text
tools/dev_impact.py:173  DESIGN_SURFACES - a contract, the spec,
                         a hook, a skill
tools/dev_impact.py:190  "design-review" if reasons else "self-review"
```

and `design-review`'s protocol opens on a page:

> 1. **A page with every plane.** The `measure` skill's two-plane
>    capture, exported and served
> 2. **Seven pictures, fixed.** 1440x900 viewport: landing, header
>    and rail, the decision, next steps, one element card ...

Its report head is `design review  the surface reviewed and the export
or served page it came from`. There is no clause for a diff that edits
a skill's prose, so the routed session either runs a page protocol
against a page its diff never touched — a picture of something else,
which is fixing guide §5's shape — or does not run it and says so.

The population is not one diff. Of the commits on `main` since
2026-08-01 that reach a `DESIGN_SURFACES` path:

```text
$ git log --format=%H --since=2026-08-01 origin/main, each commit's
  `git show --name-only` split on whether a DESIGN_SURFACES path and
  a page path (bga/viewer/, .mjs, .css) are both in it:
252 commits reach a design surface, 89 touch the page too, 163 do not
```

Nearly two in three diffs the rule routes have no page in them. The
rule is right about who the reader is — a skill is read by every round
— and the protocol it routes to is about something else.

## Required Fix

One of two, stated with the count above rather than inherited:

- `design-review` gains a prose clause — what a reader pass is for a
  skill, a hook or a contract, what it measures instead of pixels, and
  a report head a guard can tell from the page one (`UX-727`'s shape);
- or `route()` names a third destination for a surface diff with no
  page in it, and the skill that destination names exists.

## Out of Scope

Changing `DESIGN_SURFACES` itself — the surfaces are right. The page
protocol's own steps. `UX-663`'s model choice.

## Acceptance Test

A diff touching only `.claude/skills/<name>/SKILL.md` routes to a
destination whose protocol can be run on it without a served page, and
a guard reads that: a mutation routing it to the page protocol reddens.

## Outcome
