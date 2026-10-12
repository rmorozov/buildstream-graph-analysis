# UX-1355: five sentences say push to main runs "all four" Pythons, and the matrix is three

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** review 38 | **Serves:** R2 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_prose_counts_the_python_matrix.py`

## Motivation

`UX-1348` dropped 3.9 to 3.11, leaving `["3.12","3.13","3.14"]` on push
(`.github/workflows/ci.yml:105`). Five sentences written under `UX-995`
still say push to main runs "all four": `CLAUDE.md:16`,
`docs/contributing/fixing-guide.md:144` and `:673`,
`.claude/skills/decompose/SKILL.md:172`, `.claude/skills/verify/SKILL.md:62`.
No guard reads the number against the matrix.

## Required Fix

Say "all three" in the five sentences, or derive the count from the
`ci.yml` matrix line. File a guard row if the count is not derived.

## Out of Scope

`pyproject.toml:191` `target-version = "py39"`, which `UX-1348` dated
as deferred. The `all four` in `CLAUDE.md:17`, which counts push-check's gates.

## Acceptance Test

`git grep -n "all four" -- CLAUDE.md .claude docs/contributing` names
no Python count, and the number matches `ci.yml:105`.

## Outcome (round 174, 2026-10-12) — 🟢 Done

**Premise:** held, and wider: the same sentences also call the pull
request's one cell "the newest Python", and since `UX-1348` it is the floor.

### The gap, measured

```text
$ git grep -n "all four\|newest Python alone" -- CLAUDE.md .claude docs/contributing   # at 1038a41a
.claude/skills/decompose/SKILL.md:171 / :172, .claude/skills/verify/SKILL.md:30 / :61 / :62,
CLAUDE.md:16 / :29, docs/contributing/fixing-guide.md:144 / :673, docs/contributing/rules.md:31
(plus measure/SKILL.md:99, CLAUDE.md:17, fixing-guide.md:41 - not Python counts)
$ sed -n 105p .github/workflows/ci.yml
python-version: ${{ fromJSON(github.event_name == 'pull_request' && '["3.12"]' || '["3.12","3.13","3.14"]') }}
```

Push runs three cells and the pull request runs `3.12`, the lowest; five
sentences said four, and seven said the pull request's cell was the newest.

### After

```text
$ git grep -n "all four" -- CLAUDE.md .claude docs/contributing
.claude/skills/measure/SKILL.md:99   (four figures, UX-584)
CLAUDE.md:17                         (push-check's four gates)
docs/contributing/fixing-guide.md:41 (four styleguide questions)
$ python3 -m pytest -q -n0 tests/unit/test_the_prose_counts_the_python_matrix.py
2 passed
```

Every push count reads "all three" and every pull-request cell "the floor
Python alone"; the guard derives both words from `ci.yml`'s two lists.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| A1 | the prose at `1038a41a` (`git stash`) | both clauses, 2 failed |
| A2 | `"3.15"` appended to the push list, prose unchanged | `test_every_push_count_names_the_push_matrix` |
| A3 | `rules.md:31` back to "the newest Python alone" | `test_every_pull_request_cell_is_named_for_where_it_sits` |

Each clause also asserts a floor on how many sentences it matched (4 and
5), so a pattern that stops reading the prose reds instead of passing on none.

### Deviation from the Required Fix

The count is derived by the guard rather than in the prose; "newest" to
"floor" in the same sentences is the one widening, the same drift `UX-1348` left.
