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

## Outcome

**Gap measured** (`tests/browser.py`, a read-only copy of the walk
capture's `export-cold.html`): `#readers` present, 5 rows repeating
`select[name=reader]`'s 5 options label for label, every `option`'s
`title` `null`.

**Close measured** (`bga.cli view tests/fixtures/macro_micro/run
--export`, then the same script): `hasSection: false`; every option's
`title` equals its reader's `question` (e.g. `"I own the machines it
runs on"` titled `"What should the fleet be configured as?"`); choosing
the last option still draws `[data-role=reader-lead]` with
`data-reader="capacity-operator"` and its text opening on the question.
`python3 -m pytest tests/unit/test_the_readers_are_drawn_once.py
--durations=0`: 6 passed in 2.34s (golden 4 readers, macro_micro 5).

**Draw path.** `readers` is a top-level payload key with `COLUMNS`
declared, so `sections.js`'s generic `render()` drew it for every
payload regardless of `chapters.js`'s list (which only orders an
already-rendered section; `readers`' `RAIL: 'decide'` would have put a
delisted-only section right back via `RAIL_CHAPTER`). The fix uses the
existing `DRAWN_ELSEWHERE` map (`sections.js`, §1b's "reaches a reader
elsewhere" mechanism) plus the `chapters.js` delist and `decision.js`'s
`option.title`.

**Mutation table**

| guard | mutation | reddened | count |
|---|---|---|---|
| `test_the_readers_are_drawn_once.py::TestTheReadersSectionIsGone` | drop `readers` from `sections.js`'s `DRAWN_ELSEWHERE` | `test_no_readers_section[golden]`, `[macro_micro]` | 2 of 6 |
| `test_the_readers_are_drawn_once.py::TestThePickerCarriesTheQuestion` | `decision.js`: `if (question)` → `if (false)` before `option.title = question` | `test_every_option_titles_its_question[golden]`, `[macro_micro]` | 2 of 6 |

Both restored from a saved copy (not `git checkout --`), reran green.

**Extra surfaces** (against the Decomposition, which names
`chapters.js` and `decision.js` only): `bga/viewer/sections.js`
(`DRAWN_ELSEWHERE`, the only way to stop the generic per-key render);
`tests/unit/test_the_rail_takes_a_step.py` and
`tests/unit/test_the_rail_and_the_jump_box_write_the_anchor.py`, whose
rail-order array and jump-box query hard-coded `readers` as their
"not the first section" example — updated to `evidence`, the section
that now follows `decision`, per the coordinator's decision (option a);
`tests/unit/test_every_skip_reason_is_declared.py` (`UNRESOLVABLE`
68→69, a 49th browser guard) and `docs/contributing/fixing-guide.md`
(`dev_touching.py --spread --write`, 530→531 test files) — both derived
counts a new tracked test file moves.

**Not touched:** `tests/tiers.py` (the new guard's tier row is the
orchestrator's, per the track rules) — `test_the_tiers_are_a_partition.py::test_every_browser_guard_is_listed`
still names `tests/unit/test_the_readers_are_drawn_once.py` as
unlisted; `--durations=0` above is the number for that row.
