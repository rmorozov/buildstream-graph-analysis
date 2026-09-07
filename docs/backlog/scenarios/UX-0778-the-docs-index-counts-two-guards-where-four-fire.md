# UX-778: the docs index counts two guards where four fire

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-584 (which fixed this sentence's twin one document over) | **Serves:** the reader deciding which style rules are mechanical and which are honour-system | **Topic:** docs | **Area:** unassigned | **Shape:** bounded

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

_Not started._
