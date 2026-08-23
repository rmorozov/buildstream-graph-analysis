# UX-237: documentation debt has no way into the backlog

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-233 (the rule it extends) | **Serves:** the maintainers; R8 when the next big change is priced | **Topic:** docs

## Motivation

The user's observation, and it is the *general* form of what `UX-233`
fixed in one place. The fixing guide has two escape valves for work a
session cannot do now:

- item 2.5 — an unrelated **bug** you notice becomes a tracker row;
- item 9 (`UX-233`) — a change that makes `architecture.md` or the spec
  wrong is fixed **in the same commit**.

There is no third door, and documentation debt is mostly third-door
shaped: *this needs a proper explanation, and writing it well is half a
session's work.* Today that thought has nowhere to go, so it becomes a
comment, or nothing. Round 28 produced at least two instances —
`capacity_recommendation` and `memory_envelope` reach no consumer, and
`bga/whatif.py`'s convention is documented only in its own docstring —
and both survived only because the payload was made to say so out loud.

The rule that is missing: **if a change needs documentation you are not
writing now, the task goes into the backlog before the commit lands.**

## Required Fix

1. A fixing-guide item: documentation a change *needs* and does not get
   is filed as a backlog row in the same commit — id, one line, 🔴 —
   the same way item 2.5 handles a bug. Naming the gap is the minimum;
   a task file can come later.
2. The style guide states the counterpart: a document that describes
   something the code no longer does is a filing, not a silent edit, if
   the correction is bigger than a sentence.
3. A guard for the mechanical half: an `Out of Scope` or an Outcome
   section that says "documented later", "a filing waiting to happen"
   or equivalent must name the id it was filed as.

## Out of Scope

- Making every docstring a backlog item. The rule is about
  documentation a *reader outside the code* needs, not about comments.
- Retroactively filing for the whole history. The rule starts where it
  lands; mining 235 closed filings for undocumented mechanisms is a
  review round's job (`UX-241`), not this one's.

## Acceptance Test

The fixing guide and style guide carry the rule; the guard reddens on a
task file that defers documentation without naming where it went; the
two round-28 instances are filed (or explicitly declined with a
reason).
