# UX-1333: the `compare/v2` schema description lists four verdicts and the code emits a fifth, `different work`

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** review 37, checklist items 1 and 2 (2026-10-03) | **Serves:** R1, R4 | **Topic:** contracts | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`UX-1323` added `different work` to `compare.py`'s verdict labels, `cli.md:1218`, `README.md` and `real-project.md`. The published description a consumer reads from `bga compare --schema` was not touched:

```text
$ git grep -n "different_work\|different work" -- bga/compare.py bga/schemas.py docs/guides/json-contracts.md docs/guides/ci-comment.md
bga/compare.py:91:      "different_work": "different work",
$ sed -n 6948,6953p bga/schemas.py
"... which is `improved`, `regressed`, `no significant change`, `within the baseline set's own observed range`, or a `not comparable (...)` refusal."
```

A CI gate that switches on the verdict string learns the fifth value from a run, not from the schema; `ci-comment.md` and `json-contracts.md` name none of the verdicts.

## Required Fix

Derive the schema sentence from `compare.py`'s verdict-label table, so a sixth label cannot be added without it; name `different work` and what it means once in `json-contracts.md`'s compare section and in `ci-comment.md` where the comment's verdict line is described.

## Out of Scope

Changing when `different work` is returned (`UX-1323`).

## Acceptance Test

A guard reads every label in `compare.py`'s verdict table against the `compare/v2` description and `cli.md`'s verdict sentence; mutating the table (a new label) reddens it.

## Outcome

Not yet worked.
