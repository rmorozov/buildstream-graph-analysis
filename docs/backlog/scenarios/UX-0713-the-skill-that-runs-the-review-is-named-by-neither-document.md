# UX-713: the skill that runs the review is named by neither document

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-240 (the skills), UX-241 (the cadence), UX-505 (the rules card as entry point) | **Found by:** architecture review 17, by needing the skill and not finding it named | **Serves:** the session the cadence guard has just stopped | **Topic:** docs | **Shape:** judgement

## Motivation

The cadence guard reddens a round's CI and says:

```text
26 scenarios have closed since review 16 (2026-09-04), against a bound
of 25. Run a review: the checklist is in docs/audits/architecture-review.
```

It sends the session to the **checklist**. There is also a `review`
skill — the method, with the commands that answer each checklist item —
and neither document a stopped session reads will name it:

```console
$ for s in $(ls -d .claude/skills/*/ | sed 's|.*skills/||;s|/||'); do
      grep -q "\`$s\`" CLAUDE.md || echo "MISSING: $s"; done
MISSING: review

$ grep -c "skill" docs/audits/architecture-review.md
1                       # and that one is about a Perfetto query column
```

Eight of nine skills are named in `CLAUDE.md`'s pipeline. The missing
one is the only skill a **guard forces a round to run**.

Nothing reads the list, either. `test_the_agent_configuration_holds.py`
asserts `CLAUDE.md` points at the rules card and stays under a page; it
has no clause that every skill on disk is reachable from it, and
`UX-471` deliberately removed a *count* of skills because a count
decays. A membership check does not decay.

## Required Fix

`CLAUDE.md`'s pipeline names `review` beside `walk` and `design-review`,
which it already names; the cadence guard's message names the skill as
well as the checklist, since that message is what a stopped session
reads first. And a clause asserts every directory under
`.claude/skills/` is named in `CLAUDE.md` — membership, not a count.

## Out of Scope

- A count of skills in prose. `UX-471` removed the last one for the
  reason that still holds: it decays on every addition. Membership is
  derived from the directory listing and does not.
- The checklist's own content. Declined because review 17 ran it and
  found it sound; this row is about reaching the method, not the
  method itself.
- Whether the bound of 25 is right — `UX-241` sized it, and this row is
  about reaching the method, not about when it fires.

## Acceptance Test

`CLAUDE.md` names all nine skills; adding a tenth directory under
`.claude/skills/` and not naming it reddens a clause. Mutation: remove
`review` from `CLAUDE.md` — the clause reddens naming it.
