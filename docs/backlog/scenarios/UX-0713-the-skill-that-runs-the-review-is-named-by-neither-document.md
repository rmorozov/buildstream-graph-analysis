# UX-713: the skill that runs the review is named by neither document

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-240 (the skills), UX-241 (the cadence), UX-505 (the rules card as entry point) | **Found by:** architecture review 17, by needing the skill and not finding it named | **Serves:** the session the cadence guard has just stopped | **Topic:** docs | **Area:** tools | **Shape:** judgement

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

## Outcome

**The gap, measured.** `.claude/skills/` now holds ten directories
(`self-review` shipped after this row was filed) and `CLAUDE.md`
named neither the checklist's method nor the newer one:

```console
$ for s in $(ls -d .claude/skills/*/ | sed 's|.*skills/||;s|/||'); do
    grep -q "\`$s\`" CLAUDE.md || echo "MISSING: $s"; done
MISSING: review
MISSING: self-review
```

The cadence guard's message still sent a stopped session to the
checklist alone.

**The close, measured.** Same command, zero misses:

```console
$ for s in $(ls -d .claude/skills/*/ | sed 's|.*skills/||;s|/||'); do
    grep -q "\`$s\`" CLAUDE.md || echo "MISSING: $s"; done
$ echo $?
0
```

`CLAUDE.md`'s pipeline line now reads `... verify (which calls
self-review last) run inside a track ... walk, design-review and
review audit the page`. The cadence guard's message (built by a new
`_cadence_message()` in `test_the_review_has_a_cadence.py`) now ends
`"...docs/audits/architecture-review.md, and the \`review\` skill
runs it."`

**Mutations.**

| mutation | reddened | count |
|---|---|---|
| remove `review` from `CLAUDE.md`'s pipeline line | `test_every_skill_directory_is_named_in_claude_md` | 1 failed |
| drop `` and the `review` skill runs it`` from `_cadence_message` | `test_the_cadence_message_names_the_skill_as_well_as_the_checklist` | 1 failed, 8 passed |

Both reverted from a scratch copy (not `git checkout --`); both green
after.

**Deviation.** The row's own motivation counted nine skills and one
missing name; the tree had grown a tenth (`self-review`, `UX-701`)
since filing, also unnamed. The membership clause and the fix cover
both, which is what "membership, not a count" buys.
