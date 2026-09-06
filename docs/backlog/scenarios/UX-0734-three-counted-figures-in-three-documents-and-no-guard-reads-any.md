# UX-734: three counted figures in three documents, and no guard reads any

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-549 (which built the sweep these three join), UX-569, UX-576 | **Serves:** the next reader who takes one of these numbers as arithmetic | **Topic:** docs | **Shape:** judgement | **Area:** tools

## Motivation

Architecture review 18, checklist item 3. Three documents state a
count in prose; each count is derivable from a population already in
the tree; no guard reads any of the three sentences. Two are true
today and one is wrong — which is the pattern `UX-549` named, because
a true bare number and a stale one read alike.

```console
$ sed -n '83p' docs/design/styleguide.md
Twenty hints, and this table is the one place they are all written

$ awk '/^## 1a\./,/^## [^1]/' docs/design/styleguide.md | grep -c '^| `bga:'
20
```

True today, and the *only* half of that sentence nothing holds: the
table beside it is held equal to the emitted set **in both
directions** by `test_the_contract_names_its_vocabulary.py`. The
twenty-first hint therefore moves the table under a word that stays
"Twenty" — the same guard that keeps the table right is what walks
the numeral out of true.

```console
$ sed -n '41p' docs/audits/agent-runs.md
What the twenty-four rows already say: a researcher that reads a document

$ awk '/^\| /{n++} END{print n-2}' docs/audits/agent-runs.md
25
```

Wrong by one, and the population is that document's own table.

```console
$ grep -o "Parts 0-40[^|]*" docs/README.md
Parts 0-40, invariants `I1`-`I13`

$ grep -c "^# Part " docs/spec/specification.md
45
$ grep "^# Part " docs/spec/specification.md | tail -1
# Part 44 — Final Semantic Contract
```

Four Parts out. The `I1`-`I13` half beside it is correct — one stale
number next to one true one, which is exactly the pair `UX-569`
found in `architecture.md`'s opening and for the same reason.

## Required Fix

Three classes in `tests/unit/test_a_counted_figure_is_derived.py`,
each reading the source the sentence copies:

- the hint count off §1a's table rows — the same population
  `test_the_contract_names_its_vocabulary.py` already holds equal to
  `bga/schemas.py`, so the numeral cannot outlive the table;
- `agent-runs.md`'s row count off its own table;
- the spec Part range off `grep "^# Part "`, both ends, so the
  sentence names the last Part rather than a remembered one. The
  invariant range beside it is correct and joins the same clause —
  restating a true figure beside a derived one is how this one got
  here.

`WORDS` already spells to thirty; the Part range is written in
digits and needs none.

## Out of Scope

- The three sentences' wording beyond the figure. A review files; the
  fix rewrites the sentence to be derivable, not to read better.
- Any figure in `docs/backlog/` or `docs/audits/` other than the
  `agent-runs.md` row count. A pasted measurement in a task file is a
  dated fact and is never rewritten (`_counted_files`' own rule) —
  `agent-runs.md:41` is prose about the table below it, not a
  measurement of a run.

## Acceptance Test

Each of the three sentences is derived from its population, and each
new clause reds when that population moves. Mutations: add a row to
§1a's table without touching the word; add a row to `agent-runs.md`;
add `# Part 45` to a scratch copy of the spec.
