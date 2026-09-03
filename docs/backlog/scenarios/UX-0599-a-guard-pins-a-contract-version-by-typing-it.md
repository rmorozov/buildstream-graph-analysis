# UX-599: a guard pins a contract version by typing it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-584 (the figures that derive), UX-233 (the contracts guard) | **Serves:** the next contract bump, which will pass a guard that should have caught it | **Topic:** guards

## Motivation

`UX-584` made the process documents derive their versions from
`bga/schemas.py`. One literal survived, in a guard:

```text
tests/unit/test_docs_links_and_commands.py:808   assert "analyze/v2" in guide
bga/schemas.py                                    analyze/v5, compare/v2, blast/v2
```

The clause is green because §3.7 keeps `analyze/v2` as *history* — the
sentence is about what the version was. But the guard asserts the
literal rather than reading the registry, so it holds a string and not
a fact: bump `analyze` again and this clause says nothing, while the
sentence it guards may or may not still be true.

## Required Fix

The clause reads `bga/schemas.py` for the version it asserts, the way
`UX-584`'s derived clauses do, and states in one line whether it is
checking the current version or a historical one.

## Out of Scope

- The §3.7 history sentence itself — declined: `UX-584` dated it and it is correct.

## Acceptance Test

Mutation: bump a contract in `bga/schemas.py` — the clause reds or
says why the literal is historical; today it does neither.

## Outcome

**Gap measured** (`8f51a26`, worktree). The literal was where the
Motivation said, one line, and the registry three bumps past it:

```text
$ grep -n 'analyze/v2' tests/unit/test_docs_links_and_commands.py
808:    assert "analyze/v2" in guide
$ grep -n 'ANALYZE = \|SUPERSEDED = ' bga/schemas.py
71:ANALYZE = "analyze/v5"
82:SUPERSEDED = ("analyze/v4", "analyze/v3", "analyze/v2", "compare/v1",
```

The Acceptance Test, before: `ANALYZE` bumped to `analyze/v6` with
`v5` added to `SUPERSEDED` — the clause said nothing.

```text
$ pytest ...::test_the_fixing_guide_names_the_output_versioning_rule -q
1 passed in 0.11s
```

**Close measured.** The clause reads §3.7 *after* its pinning clause
and requires every contract id there to be one `contracts.superseded()`
lists — so it states, and derives, that it is checking a **historical**
version. The pinning half stays with `UX-584`'s guard; two guards on
one sentence is how the two disagree. Same bump, after:

```text
$ pytest ...::test_the_fixing_guide_names_the_output_versioning_rule -q -rA
PASSED tests/unit/test_docs_links_and_commands.py::test_the_fixing_guide_names_the_output_versioning_rule
1 passed in 0.31s
$ pytest tests/unit/test_the_process_documents_derive_their_figures.py -q
FAILED ...::test_the_guide_pins_a_version_that_is_not_superseded
FAILED ...::test_the_document_carries_the_derived_sentence[docs/contributing/fixing-guide.md]
2 failed, 10 passed in 0.39s
```

The bump reds the clause that owns the live ids and leaves the history
green, which is the distinction the item asked for.

| mutation | anchor | reddened | run printed |
|---|---|---|---|
| §3.7 history: `analyze/v2` → `analyze/v5` (the live id) | `grep -c 'report to \`analyze/v5\`'` → 1 | `§3.7's history names ['analyze/v5'], which \`bga/schemas.py\` does not list as superseded` | `1 failed in 0.28s` |
| `schemas.SUPERSEDED`: drop `"analyze/v2"` | `SUPERSEDED = ("analyze/v4", "analyze/v3", "compare/v1",` | `§3.7's history names ['analyze/v2'] …` — proves the registry is read, not a literal | `1 failed in 0.34s` |
| §3.7 history: delete the `UX-288` id sentence | `grep -c 'The first bump removed'` → 1 | `§3.7's history names no contract id` (the vacuity refusal) | `1 failed in 0.27s` |

**A guard that did not discriminate.** The first writing also asserted
`schemas.ANALYZE not in named`. Measured: on the live-id mutation the
`superseded()` clause fires first and this one never runs — the current
id is by construction never in `SUPERSEDED`, so it can only fire on a
`schemas.py` that contradicts itself. Removed; the current version now
appears in the failure message, where it informs without pretending to
assert.

**Close:** `make test-touching` 12 files, 418 passed, 3 skipped in
9.71s. `make test-medium` (the file's tier) 2322 passed, 53 skipped in
217.55s. `make lint` clean. `make test` not run — the orchestrator's.

**Deviation from the Required Fix:** none. The §3.7 sentence was not
touched (Out of Scope); the two mutations against it were reverted, and
`git status` is clean of both it and `bga/schemas.py`.
