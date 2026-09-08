# UX-771: two more documents number sections, and no guard reads them

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-763 (the guard this widens) | **Serves:** the round that renames a section and learns which id was taken from CI | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

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

**Gap measured.** `_sections()`'s scope was three named paths
(`STYLEGUIDE`, `FIXING_GUIDE`, `STYLE_GUIDE`); `verify/SKILL.md`
(§1-§7) and `decompose/SKILL.md` (§0-§5) numbered sections the same
way and were cited the same way (`decompose §3` in three tracked
files, `verify §7` in two) and were invisible to the census.

**Close measured.** `_process_documents()` derives the population: a
candidate is under `docs/design/`, `docs/contributing/`, or a
`SKILL.md`, numbers ≥2 sections at ≥50% of its `##`/`###` headings
(excludes `architecture.md` 22%, `directions.md` 4%), and is cited
elsewhere as `<name> §N` for an `N` it actually numbers (excludes
`review`/`self-review`, both 100% numbered but cited only at ids past
their own highest — `review §6/§7`, `review §10`, none in `{1..5}`).
Result: exactly `{styleguide, fixing-guide, style-guide, verify,
decompose}`. `KNOWN_AMBIGUOUS` now names `(id, owners)`, not a bare id,
so an owner set changing reds with no new id needed. A verifier found
`_cites_own_id`'s alias match had no left word boundary: `self-review`
ends in `review`, so a file citing only the former would silently pull
`review/SKILL.md` in with no citation of `review` ever written -
fixed with `r"(?<![\w-])"`, and confirmed a citation naming `review`
itself at one of its own ids still pulls it in (that half is intended,
not a surprise).

```console
$ python3 -m pytest tests/unit/test_the_styleguide_names_its_guards.py -q
.............
13 passed in 1.30s
```

**Mutation table:**

| # | mutation | reddened | count |
|---|---|---|---|
| 1 | `## 7. Something` appended to `decompose/SKILL.md` | `test_no_new_id_is_shared_across_the_process_documents` naming `('7', ('decompose', 'fixing-guide', 'style-guide', 'styleguide', 'verify'))`; `test_the_known_set_is_not_stale` naming the old 4-owner `'7'` row | 2 failed, 10 passed |
| 2 | removed `("4a", ("fixing-guide", "styleguide"))` from `KNOWN_AMBIGUOUS` | `test_no_new_id_is_shared_across_the_process_documents` naming exactly `('4a', ('fixing-guide', 'styleguide'))` | 1 failed, 11 passed |
| 3 | `_process_documents()` narrowed to `{STYLEGUIDE, FIXING_GUIDE, STYLE_GUIDE}` | all three census/population tests: 7 owner-sets shrank (extra), 7 stale (gone), population `!= {..., verify, decompose}` | 3 failed, 9 passed |
| 4 | left word boundary stripped from `cite`'s regex | `test_self_review_cannot_stand_in_for_review`: a probe naming only `self-review` at one of `review`'s own ids pulled `review` in | 1 failed, 12 passed |

Each reverted from its pre-mutation copy; full count passed after each.
Mutation 4 uses a hermetic `tmp_path` probe, not today's corpus - the
corpus has no citation naming `self-review` alone at one of `review`'s
own ids, so a guard reading only it
would pass with the bug present.

**Deviation.** The heading-shape rule alone was not enough - `review`
and `self-review` also number ≥50% of their headings but are never
cited at an id they hold, so a second, checkable rule
(`_cites_own_id`) does the real discriminating the task asked for
rather than a hand-picked exclusion list of two more names. Separately,
the same verifier found `cite`'s regex also matches inside fenced code
blocks; measured against today's corpus this changes nothing - both
`verify §7` (`decompose/SKILL.md`'s table) and `decompose §3`
(`closed.md`) have a genuine non-fenced citation each - so it is
latent, not live, and is left unfixed rather than made a second,
unmeasured change in this commit. `_cites_own_id` scans this task file
too, tracked and live the moment it is saved - an early draft of this
very Outcome named `review` and `self-review` directly beside one of
`review`'s own ids to illustrate the fix, and both entered the real
population as a result; rephrased with the name and the id apart.
