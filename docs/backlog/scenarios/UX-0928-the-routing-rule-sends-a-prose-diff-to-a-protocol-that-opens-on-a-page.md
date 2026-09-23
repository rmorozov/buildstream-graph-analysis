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

**Round 138, 2026-09-23**

**Decision:** the second fix. `review` reads a document against the
tree with a command per sentence and needs no page, which is what a
skill, hook, spec or contract diff is; it lacked a scope (the diff's
hunks, not a document group), the reader's question per surface, a
report head, and an exemption from its cadence log row.

### The gap, measured

```text
$ git rev-parse --is-shallow-repository      # false
$ python3 <scratch>/count.py <rev>   # per commit since 2026-08-01: git show
  --name-only -m --first-parent; DESIGN_SURFACES read from dev_impact
c8b2f781^ (filed)   2147 commits; 252 reach a design surface, 89 touch the page too, 163 do not
origin/main dcbe4615 2173 commits; 254 reach a design surface, 89 touch the page too, 165 do not
without -m --first-parent (175 merges read as empty):
origin/main          210 reach a design surface, 69 touch the page too, 141 do not
```

The filed count reproduces exactly once a merge is read by its
first-parent diff. 165 of 254 (65 %) had nowhere runnable to go.

### After

```text
$ python3 tools/dev_impact.py .claude/skills/verify/SKILL.md --route
review  (a skill)
$ python3 tools/dev_impact.py bga/schemas.py --route
review  (a contract)
$ python3 tools/dev_impact.py bga/viewer/app.js --route
self-review
$ git diff --name-only | python3 tools/dev_impact.py - --route   # this diff
review  (a skill)
```

`route()` returns `review` for a surface diff with no
page path (`bga/viewer/`, `.mjs`, `.css`), and
`design-review` with `the page` added to its reasons when it has one.
`review` gains an unnumbered *A diff `self-review` routed here*
section: one row per `DESIGN_SURFACES` name, a `surface review` head,
no architecture-review log row. `self-review`, `verify`,
`design-review` and `CLAUDE.md`'s pipeline line say where it goes.

### Mutations verified red and reverted (3)

Guard: `tests/unit/test_the_self_review_reads_the_policy_it_has.py`,
12 clauses.

| # | mutation | reddened |
|---|---|---|
| M1 | no-page surface diff returns `design-review` (the Acceptance Test's) | 3 of 12, incl. `test_a_skill_only_diff_goes_to_a_protocol_with_no_page` |
| M2 | `if reasons and False:` — a viewer+contract diff goes to `review` | 1 of 12 |
| M3 | `review`'s `a hook` row deleted | 1 of 12, `test_the_no_page_destination_answers_every_surface` |

### Deviation

**`dev_impact.py` stays at 245 lines** (`dev_sizes.py --check`): the page
test is inline in `route()`, not a named helper.

**The section is unnumbered.** A `## 6.` pulled `review/SKILL.md` into
`test_the_styleguide_names_its_guards.py`'s id-collision population
(`directions.md:847` cites an unrelated "review §6/§7"), reddening 4
clauses; citations say "routed-diff section" instead of `§6`.
**No report-kind recogniser.** A routed run's report goes to the
session, not `docs/audits/`, so `dev_audit_reports` has nothing to
read; the head is fixed in prose only.
**`UX-701`'s `test_a_contract_diff_goes_to_design_review`** is now
`test_a_contract_diff_is_sent_on`, asserting `review`: the old
expectation is the defect.
