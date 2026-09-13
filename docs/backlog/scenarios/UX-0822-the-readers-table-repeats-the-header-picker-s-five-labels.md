# UX-822: the readers table repeats the header picker's five labels

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-668 (the picker in the header), UX-372 (the section after the decision) | **Found by:** round 115, the design review | **Serves:** anyone landing on the decision | **Topic:** viewer | **Area:** bga-viewer | **Shape:** bounded

## Motivation

`readers` (`chapters.js:86`, after `decision`) draws a table — Reader /
Their question / Leads with — whose Reader column is, label for label,
the header's `select[name=reader]` option list `UX-668` put there. On
the walk capture:

```text
readers          5 rows · "I own the dependency graph | What does the shape of
                 this graph make impossible? | chain-graph" · no control of its own
select[name=reader]   the same five labels, 411 px above it
```

Five sentences twice within one screen's scroll (§5a's repetition
budget, §5b filed this round). The table explains; the picker filters;
the reader meets the explanation before the mechanism it explains.

## Required Fix

The table goes from `bga/viewer/chapters.js` and `bga/viewer/decision.js` draws nothing for it. The picker's option `title` carries the reader's
question; the chosen reader's lead (`readerLead`) lands in the decision
panel's slot as it does today, and the rail loses the `readers` entry.
A run with fewer than two readers draws nothing, as `UX-194` already
rules.

## Decomposition

Input classes the guard covers: a run with five readers (the walk
capture), one with one reader (`tests/fixtures/one_source_many_elements`,
no picker and no table), and the golden fixture; the journey it
touches is the landing → choose a reader → the lead in
`test_the_journey_has_an_answer_key.py`.

## Out of Scope

- The `readers` payload itself — the CI comment routes on it.
- The decision panel's wording — `UX-643`.

## Acceptance Test

On the walk capture's export: `section#readers` absent; `select[name=reader]
option[title]` non-empty for every option; `.reader-lead` still lands
after a choice. Mutation: keep the section — the §5b guard reds.
