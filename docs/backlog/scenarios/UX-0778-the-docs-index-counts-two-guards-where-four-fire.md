# UX-778: the docs index counts two guards where four fire

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-584 (which fixed this sentence's twin one document over) | **Serves:** the reader deciding which style rules are mechanical and which are honour-system | **Topic:** docs | **Area:** unassigned | **Shape:** bounded

## Motivation

`docs/README.md` names two of the style guide's rules as enforced:

```console
$ sed -n '304,306p' docs/README.md
  ... style-guide.md ... Two of
  them are enforced by
  ... test_docs_links_and_commands.py ...:
$ grep -n "^def test_" tests/unit/test_docs_links_and_commands.py \
    | grep -icE "link|resolv|python.*m |padded|cell"
5
```

Four style-guide rules land in that one file: relative links resolve,
no instructional document prints `python3 -m tools.<module>`, scenario
filenames are zero-padded (rule 9), and §8's table-cell count — which
`style-guide.md:159` says this same file *owns*.

**`UX-584` already fixed this exact sentence in `style-guide.md`
itself**, and derived it: `test_the_process_documents_derive_their_
figures.py:236` counts `"**Enforced by test"` in the guide's own text
and holds the stated figure to it. The copy in `docs/README.md` was
never in that guard's population. Written 2026-08-18 and untouched
since; `grep -rn "Two of them are enforced" tests/unit/` finds only
the historical comment about the fixed copy.

So: the derivation exists, works, and reads one of the two documents
that state the figure. The population stops where its failures start —
the ninth instance of this shape counted since round 103, and the
second this session after `UX-771`.

## Required Fix

Widen `UX-584`'s derivation to both documents rather than adding a
second one. The count that matters here is not the same quantity —
`style-guide.md` counts rules that say "Enforced by test", while
`docs/README.md` counts rules **one named guard file** holds — so the
fix must decide whether those are one figure or two, and say which in
the Outcome. They are not interchangeable, and treating them as one is
how the wrong number would land again.

## Out of Scope

- Rewriting either document's prose beyond the sentence and its
  derivation — the two documents are front doors and a wider edit
  is `UX-689`'s restructuring, not a count fix.
- The other counted figures in `docs/README.md` — `test_a_counted_
  figure_is_derived.py` already holds them and review 20 re-ran it
  green (39 tests).

## Acceptance Test

Move a rule's enforcement into or out of
`test_docs_links_and_commands.py` and watch both documents' figures
move, or the guard red naming the one that did not.

## Outcome

**Gap measured:** the guide's own rows whose `**Enforced by test**`
clause is a guard inside `test_docs_links_and_commands.py`: rules 3, 5,
9, 14, plus §8's table-cell rule (named there in its own words already)
— five, not the Motivation's four, which missed rule 14 (`Out of
Scope`) — its guard,
`test_every_out_of_scope_entry_names_a_task_or_states_a_decline`, is
inside that same file. `docs/README.md` stated `Two`.

**Two figures, kept as two** (the session's decision, implemented):
`style-guide.md`'s own sentence still derives from
`rules.count("**Enforced by test")` (rule text saying enforcement
exists at all — currently 5, and includes rule 15, whose guard is
`test_a_guard_ledger_names_its_link.py`, a different file).
`docs/README.md`'s sentence derives from a new, separate population:
occurrences of the literal string
`tests/unit/test_docs_links_and_commands.py` in the guide's rule body,
which required naming that file in rules 3, 5, 9 and 14's `Enforced by
test` clauses (they said only `test.` before — §8 already named it).
That count is 5 too, today — a coincidence between two different
questions, not one figure reused; a rule enforced elsewhere (rule 15)
or a new one enforced only in this file moves them independently, which
is what mutation 2 below shows.

**Close measured:** `docs/README.md` now reads `Five of them are
enforced by … test_docs_links_and_commands.py`, spelled the way
`style-guide.md`'s own clause spells it
(`WORDS[n].capitalize()`). Both sentences are new keys/clauses in
`_derived()`, `tests/unit/test_the_process_documents_derive_their_
figures.py`.

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| README's figure off by one (`Five` → `Four`) | `TestTheFiguresAreDerived::test_the_document_carries_the_derived_sentence[docs/README.md]` only | 1 failed, 24 passed |
| rule 9's `Enforced by` moved to `test_a_file_with_three_excursions_has_a_filed_task.py` | same clause only — `docs/contributing/style-guide.md`'s own clause (index 5 unchanged, count still 5) stayed green, showing the two figures move independently | 1 failed, 24 passed |

Both restored from the scratchpad copy (not `git checkout`) and
reconfirmed green: `25 passed`.

**Deviation.** The session decided two figures; an `implementer` on `sonnet` derived both and found the Motivation's "four" was five. Its verifier read every mutation green-to-red and named one mislabel: the rule titled `Out of Scope` is §12, and §14 reuses its guard — the Outcome above says 14 where the fact belongs to 12; the counts, being literal string counts, are unaffected. Untested edge, recorded: a rule body citing the guard file twice would count twice.
