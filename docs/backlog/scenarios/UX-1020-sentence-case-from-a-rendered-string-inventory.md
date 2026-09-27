# UX-1020: every rendered label is sentence case, and a plural follows its count

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.3 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
conventions     sentence ("Collapse all"), lower ("view as JSON"),
                UPPER (rail, text-transform), Capitalised (h3.category, .question-group)
(s) plurals     element(s), core(s), builder(s), peak(s)
```

## Decomposition

Input classes: headings, labels, buttons, rail entries, counted plurals at 1 and at many. The journey extends scanning labels into reading them as one voice.

## Required Fix

First an inventory, `docs/design/rendered-strings.json`: every heading, button, `summary`, rail entry, `th` and `option` rendered on `golden`, `macro_micro`, the 1,202-element run and the served Perfetto and SQL pages, each with its role and, where it breaks the case rule, its exception class (code, unit, product name, acronym). Then sentence case throughout. No `text-transform: uppercase|capitalize` in `bga/viewer/style.css`; plurals are chosen by count.

## Out of Scope

Proper nouns and command names, which keep their case.

## Acceptance Test

`tests/unit/test_labels_are_sentence_case.py`: booted on the same pages, every rendered string of those roles is in the inventory, and each is sentence case or carries a listed exception; source has no `text-transform` on words, and no `(s)` in `innerText`. Mutations: restore `text-transform: uppercase` on the rail; add an unlisted Title Case button; delete an inventory entry. Each reds.

## Outcome

Gap measured (`grep -n text-transform bga/viewer/style.css`, before): 5 rules
(`.badge`, `h3.category`, `.toc-rail`, `button.toc-chapter-open`,
`.question-group > summary`). Live `(s)` sweep of `golden`/`macro_micro`'s
`document.body.innerText` (before): 9 occurrences across
`bga/viewer/{decision,element,views}.js` and
`bga/{correlate,findings,structural/serialization_points}.py`. Lowercase
`<th>`/header defects found the same way: 4 (`name`, `element`, `value`,
`mark`/`Value` pairs in `exhibitTwin` callers).

Close measured: `python3 -m pytest tests/unit/test_labels_are_sentence_case.py -q`
→ 5 passed. `grep -c text-transform bga/viewer/style.css` → 0. Live `(s)` sweep
(after) → 0 occurrences on either fixture. `tools/dev_rendered_strings.py --write`
→ 353 inventory rows, 0 uncased with `exception: null`.

Mutation table:

| mutation | reddened | test |
|---|---|---|
| restore `text-transform: uppercase` on `.toc-rail` | `test_no_text_transform_on_words` | 1 failed, 4 passed |
| add unlisted button `"Collapse All"` | `test_every_rendered_label_is_listed_and_cased` (both fixtures) | 2 failed, 3 passed |
| delete the `"Collapse all"` inventory row | `test_every_rendered_label_is_listed_and_cased` (both fixtures) | 2 failed, 3 passed |
| restore `builder(s)` in `correlate.py`'s knee sentence | `test_no_parenthesised_plural_reaches_the_page` | 1 failed, 4 passed |

Each reverted from a copy; `test_labels_are_sentence_case.py` returned to
5 passed after every mutation.

Deviation: the inventory covers `golden` and `macro_micro`, not the 1,202-element run or the Perfetto and SQL pages the Required Fix names (a bookkeeping line). The `(s)` plurals in CLI output outside the viewer are untouched, filed as `UX-1038`.

Follow-up (#295): `tools/dev_rendered_strings.py` and
`test_labels_are_sentence_case.py` now also walk `scale_run` (the
1,202-element run, built once per module) and the served
`perfetto.html`/`sql.html`. `--write` → 382 rows (was 353). Found and
fixed: three `+N more <noun> (...)` viewer controls
(`nav.js`, `structured.js` x2, `views.js`) not sentence case, only
reachable at this scale; two pinned tests updated to match. Bookkeeping
line `bf5e42b` marked `swept r142 UX-1020`.
