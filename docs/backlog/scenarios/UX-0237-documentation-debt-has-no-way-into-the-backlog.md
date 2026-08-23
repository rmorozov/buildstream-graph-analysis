# UX-237: documentation debt has no way into the backlog

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-233 (the rule it extends) | **Serves:** the maintainers; R8 when the next big change is priced | **Topic:** docs

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

## Outcome

**Status:** 🟢 Fixed & Verified

The third door exists. Definition of Done item 11 says documentation a
change needs and does not get is filed before the commit lands — a row
in the index, id, one line, 🔴, topic `docs` — the same shape and the
same cost as `§2.5`'s rule for a bug you noticed. Style-guide rule 14
is the counterpart from the writing side: a correction bigger than a
sentence is a filing, not a silent rewrite, because the alternative is
a session that started as "fix one line" turning into a rewrite nobody
reviewed.

Both say the same thing about declining: **a stated decline is a
decision and silence is not.** That is the whole difference between
this rule and the comment it replaces.

### The three that motivated it are rows now

Measured before filing — the evidence the rule was built on:

```text
git grep -l capacity_recommendation docs/ -> 3 backlog files, no guide, no spec
git grep -l memory_envelope docs/         -> 4 backlog files, no guide, no spec
git grep -l "upper bound, not a forecast" docs/  -> nothing
```

`UX-242` (the capacity recommendation), `UX-243` (the memory envelope)
and `UX-244` (what-if's convention). `UX-243` is the sharpest of the
three: `README.md` tells a reader peak memory "is what decides whether
`--builders` can go up" and names no field, so a reader who believes
that sentence has nowhere to go next.

### Two of my own guards did not discriminate

Both were the same failure, and it is the one this round keeps
producing — a guard over prose matching the sentence that *argues for*
the thing it is checking.

The deferral check read whole filings, and so matched `UX-237`'s own
Required Fix — the sentence that lists the phrases the guard looks
for. It reads `Out of Scope` and `Outcome` only now, which is where a
deferral is actually written and what the filing asked for.

Worse, `test_the_round_28_instances_were_filed` searched every filing
for each mechanism name. Deleting `UX-243` entirely left it **green**,
twice over: `memory_envelope` appears in `UX-237`'s Motivation as the
evidence, and again in `UX-242`'s `Out of Scope` pointing at its
sibling. It pins the mechanism-to-filing pairing now and checks the row
exists too — measured red on both, a deleted filing and a deleted row.

That is the fourth and fifth instance of this shape in one round
(`UX-231`, `UX-233`, `UX-239`, and these two). The rule `UX-239` wrote
holds: **when a guard reads prose, say which part of the document is
the subject and which part is the argument** — and the corollary this
one adds, that a filing which cites evidence contains that evidence, so
searching "all filings" for it proves nothing.

### One thing found on the way

The Definition of Done had two items numbered `4`, so every in-text
cross-reference below it ("the same reason item 5 is") pointed one item
wrong in the rendered document. Renumbered to 1-12, the reference
corrected to item 6, and a guard now asserts the list numbers
sequentially — cheap, and the list is cross-referenced by number.

**Mutations verified red and reverted (6):** the fixing-guide rule
removed; rule 14 no longer pointing at its counterpart; the duplicate
item number restored; a filing deferring documentation with no id; the
deferral pattern emptied; a round-28 filing deleted, and separately its
row.

**Deviation from the Required Fix:** none.

Small tier: `2005 passed, 1130 deselected in 21.30s`.
Full suite: `3132 passed, 3 skipped in 310.51s`. `make lint`: clean.
