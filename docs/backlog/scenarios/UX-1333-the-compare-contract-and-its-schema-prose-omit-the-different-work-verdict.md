# UX-1333: the `compare/v2` schema description lists four verdicts and the code emits a fifth, `different work`

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** review 37, checklist items 1 and 2 (2026-10-03) | **Serves:** R1, R4 | **Topic:** contracts | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** test_the_compare_schema_names_every_verdict.py

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

**Gap measured.** `compare/v2`'s description named 4 of the 5 labels in `compare.VERDICT_SENTENCES`; `json-contracts.md` and `ci-comment.md` named 0 of them.

**Close measured.** The description is built from `VERDICT_SENTENCES` by `schemas._compare_verdict_list()` (lazy import; `compare` imports `schemas`): `bga compare --schema | jq .description` lists all 5 plus the `not comparable (...)` refusal. `json-contracts.md` gains a `verdict` row and `ci-comment.md`'s headline bullet lists the labels, `different work` explained once in each.

`python3 -m pytest -n 0 tests/unit/test_the_compare_schema_names_every_verdict.py` : 3 passed. It reads each label against the description, `cli.md`'s "The verdict is one of" sentence, and both guides.

| mutation | result |
|---|---|
| compare.py: add a sixth label to `VERDICT_SENTENCES` | 2 failed, 4 passed (`cli.md` sentence, both guides; the schema follows by derivation, so stays green) |
| schemas.py: description back to a typed two-label list | 1 failed, 5 passed (`test_the_schema_description_names_every_label`) |

**Deviation.** None.
