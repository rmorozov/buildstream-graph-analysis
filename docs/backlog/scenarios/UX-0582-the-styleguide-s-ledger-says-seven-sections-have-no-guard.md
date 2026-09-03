# UX-582: the styleguide's ledger says seven sections have no guard

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-305 (the conformance checklist), UX-320 | **Serves:** the session that touches the page and reads §7 to find its guard | **Topic:** docs

## Motivation

Thirty-one guard files enforce the styleguide (539 passed, 8 skipped
without the example capture), and the guide's own §7 ledger
(`styleguide.md:1305-1333`) says "none with a guard yet" for seven
sections that have had one since rounds 59-70 (§1c/§1d, §2c-§2e,
§6b-§6d). **Round 83 corrects that parenthetical in place**: the seven
§7 actually calls guardless are §1c, §3f, §4d, §5a (round 58) and §1d,
§3g, §4e (round 69) — §2c-§2e and §6b-§6d are not among them, and §2d,
§6b, §6c, §6d are listed by §7 *with* guards. Of the real seven, four
have a guard citing them (§1c, §3f, §3g, §4e) and three do not (§1d,
§4d, §5a), so "seven sections have no guard" is falsified as a count
and held as a defect. Beside it: §3's "default 20" row cap has no constant to
point at (`grep -rn "\b20\b" structured.js tables.js schemas.py` →
a comment), §6b says 21 modules where there are 22, and §1's guard
checks module→guide in one direction only — the scalar rows (badge,
sentence, popover, banner, delta) have no `classify` row and no
reverse check.

## Required Fix

§7's prose ledgers replaced by one §→guard table, derived: a guard
reads `§[0-9][a-g]?` mentions across `tests/unit/*.py` and holds
the table to them both ways (a § with no guard is listed as such
with a reason; a guard citing a § that the table omits is red). The
"default 20" sentence names its constant or loses the number; §6b's
count derives.

## Out of Scope

- New rules — this is the index of the ones that exist.

## Acceptance Test

Mutation: delete a §-citing guard file — the table reds on that row;
add a § to the guide with no guard and no reason — red.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** falsified — §7 does say seven sections have no guard, but
four of the seven do (§1c, §3f, §3g, §4e), and the Motivation's
parenthetical named the wrong seven. Corrected in place above.

The gap, measured before the change:

```text
$ grep -cE '^#{2,3} [0-9]+[a-g]?\. ' docs/design/styleguide.md
33
$ git ls-files 'tests/unit/*.py' | wc -l
436
  ... of those, containing a §[0-9][a-g]? mention                 48
  sections §7 called guardless    §1c §3f §4d §5a §1d §3g §4e      7
  ... of those, with a guard citing them  §1c §3f §3g §4e          4
$ git ls-files -- 'bga/viewer/*.js' | wc -l
22                          §6b's prose said 21
$ grep -rn 'TABLE_OPENS_BOUNDED_ABOVE' bga/viewer/structured.js | tail -1
1430:export const TABLE_OPENS_BOUNDED_ABOVE = 40;   §3 said "default 20"
```

Closed: §7's three prose ledgers are one §→guard table over all 33
sections; `tests/unit/test_the_styleguide_names_its_guards.py` holds it
to the scan both ways. §3's row cap names `TABLE_OPENS_BOUNDED_ABOVE`
and `openingBound` instead of a number no constant had; §6b's two
counts are a command block the guard re-runs.

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_styleguide_names_its_guards.py -q
9 passed in 0.12s
$ make test-touching
20 file(s) selected · 488 passed, 5 skipped in 49.77s
$ make lint
All checks passed!
```

**Nine ids are named, not derived.** `§1`-`§7`, `§4a` and `§6a` are
headings in `fixing-guide.md` too, and a bare `§5` in a guard belongs
to whichever document the sentence is about — measured: all ten files
citing `§5` mean the fixing guide's. Those rows are held to existing
and citing; the exclusion set is the intersection of the two documents'
own headings, so a renumber moves it. This file is excluded from its
own scan: it quotes ids to report them.

**Mutations verified red and reverted (9):**

| mutation | reddened | run |
|---|---|---|
| `\| §2e \| \| no guard cites it \|` → empty note | `test_a_row_with_no_guard_gives_a_reason`: `rows name no guard and give no reason: ['2e']` | 1 failed, 8 passed |
| §1b's row loses its guard, keeps a reason | `test_no_guard_cites_a_section_the_table_omits`: `§1b is cited by ['test_the_merge_carries_every_field.py']` | 1 failed, 8 passed |
| `rm tests/unit/test_the_page_has_a_volume_budget.py` (acceptance) | `test_every_named_guard_exists_and_cites_its_section`: `§3e: … is gone`, and the row's reverse clause | 2 failed, 7 passed |
| `## 4f.` added to the guide, no row (acceptance) | `test_every_section_has_a_row`: `sections with no row: ['4f']` | 1 failed, 8 passed |
| `named` written on §1b's row | `test_a_row_is_named_exactly_when_the_scan_cannot_attribute_it`: `['§1b']` | 1 failed, 8 passed |
| "first N rows" → "first 20 rows" | `test_the_row_cap_names_its_constant`: `restates ['20']` | 1 failed, 8 passed |
| `TABLE_OPENS_BOUNDED_ABOVE` → `…_AT` in §3 | same guard: `the viewer has no such identifier` | 1 failed, 8 passed |
| §6b's `22 viewer modules` → `21` | `test_the_module_count_derives`: `§6b says 21 …; git ls-files says 22` | 1 failed, 8 passed |
| `§4f` planted in `test_the_mapping_is_law.py` | `test_a_cited_section_exists_in_one_of_the_two_documents` | 1 failed, 8 passed |

**Vacuity.** `_unit_tests()`'s pattern narrowed to match nothing:
`test_the_scan_reads_something` red at `the population is 0 files`, and
`test_no_guard_cites_a_section_the_table_omits` red on every row
(`§1a's row names … and nothing cites it`) — an empty scan cannot pass.

**A guard of mine that did not discriminate.** The first `rm` of a
guard file reddened with `FileNotFoundError` from inside `_cited` — red
for the wrong reason (`git ls-files` still names an uncommitted
deletion). The scan now skips paths that are gone and the row check
reports `is gone`; the mutation was re-run and the message names §3e.

**Deviation from the Required Fix:** the both-ways scan covers 24 of 33
sections; the nine the fixing guide also numbers are `named`. §1's
missing reverse `classify` check (Motivation, last clause) was not in
the Required Fix and is untouched. `tests/tiers.py` and
`tests/ci_reference.json` are the orchestrator's after the merge; the
new file runs 0.12s single-process, which is the small tier's default.

**Suite:** `make test` not run in this track — the orchestrator runs it
for the batch. Tier and touching lines are above.
