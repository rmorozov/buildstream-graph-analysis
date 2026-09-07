# UX-771: two more documents number sections, and no guard reads them

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-763 (the guard this widens) | **Serves:** the round that renames a section and learns which id was taken from CI | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-763` widened `_ambiguous()` from one document against the union to
pairwise overlap across three, and added a census guard so a new shared
id reds naming itself. Its verifier then found the population is still
narrower than the sentence:

```console
$ grep -rn "§[0-9]" .claude/skills/*/SKILL.md docs/backlog/scenarios/ | head
.claude/skills/decompose/SKILL.md:60:   CI only (verify §7)
docs/backlog/scenarios/UX-0501-...md:16:  files a parallel track must not touch (decompose §3)
docs/backlog/scenarios/UX-0685-...md:77:  host   CI only (verify §7)
```

`.claude/skills/verify/SKILL.md` numbers §1-§7 and
`.claude/skills/decompose/SKILL.md` numbers §0-§5, both with the same
`## N. Title` convention as the three tracked documents, and both are
cited elsewhere with the same bare `§N` notation. Their ranges already
overlap `fixing-guide.md`'s §1-§7a today, unguarded.

So the guard that exists to stop a section id meaning two things reads
three of the five documents that number sections. `UX-763`'s own
collision — §8 in the guide against §8 in `style-guide.md`, breaking
`UX-0478`'s citations — is what that gap looks like when it fires; the
next one can fire from a skill instead.

The verifier ruled out one false lead: `directions.md`'s "review §6/§7"
and "§13/§14" cite an external UX review document, not
`.claude/skills/review/SKILL.md`, whose highest section is 5.

## Required Fix

Bring the two skills into `_sections()`'s scope, extend
`KNOWN_AMBIGUOUS` with whatever overlaps exist today — each entry
corresponding to a real pair, not a blanket — and let the census guard
red on anything new. If a skill's numbering should not be in the same
id space as the guides, say why in the guard rather than by omission.

## Out of Scope

- Renumbering any skill. The overlaps that exist today are recorded,
  not repaired; this row is about seeing the next one.
- The three documents already covered — `UX-763` closed those.

## Acceptance Test

```console
$ python3 -m pytest tests/unit/test_the_styleguide_names_its_guards.py -q
```

green with the two skills in scope, and red naming the id when a new
`## N.` heading is planted in either of them.

## Outcome

(open)
