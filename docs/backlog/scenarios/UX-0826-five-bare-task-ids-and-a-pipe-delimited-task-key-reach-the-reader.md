# UX-826: five bare task ids and a pipe-delimited task key reach the reader

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-669 (the rule), UX-824 (the guard) | **Found by:** round 115, the design review | **Serves:** every reader of a finding | **Topic:** analysis | **Area:** bga | **Shape:** mechanical

## Motivation

Four sentences in the analysis carry a task id in parentheses and one
row prints an internal key:

```text
bga/correlate.py:1181   "does not model contention (UX-14), and cores-busy is an average"
scale export            UX-478 (twice), UX-345, UX-477 in rendered prose
duration_resolution     "Tasks?" row: all.bst|FETCH|FETCH|0
```

`UX-669` fixed three such sentences in round 82 and left the rule
unguarded; these are the ones it did not reach.

## Required Fix

In `bga/correlate.py` and `bga/findings.py` each citation becomes the section's question or a backticked id per
§4b, and `duration_resolution` renders the task as element · kind
(`all.bst`, FETCH) rather than the join key. `UX-824`'s guard is what
finds the next one.

## Decomposition

Input classes: a finding with a caveat sentence (the contention
caveat), a `duration_resolution` block with and without tasks, and the
golden fixture; the journey is the findings list in the answer key.

## Out of Scope

- The guard — `UX-824`.
- The section keys — `UX-825`.

## Acceptance Test

`grep -n "(UX-[0-9]*)" bga/*.py` names no reader-facing sentence, and
`tests/browser.py` counts 0 `\bUX-\d+\b` in the 1,202-element export's
text with every door and chapter opened; mutation: put one `(UX-14)`
back — the count is 1. The guard over both exports is `UX-824`'s.

## Outcome

**Gap measured.** Fixture: `bga gen-synthetic <dir> --seed 1 && bga
analyze <dir> --diagnostics && bga view <dir> --export <file>`
(1,202 elements). Command (`tests/browser.py`'s `Browser.measure`,
pasted in full below):

```python
CLOSED = "document.body.innerText.match(/\\bUX-\\d+\\b/g) || []"
OPEN_THEN_SCAN = """(() => {
  document.querySelectorAll('.description[hidden]').forEach(n => n.hidden = false);
  document.querySelectorAll('section[data-section][data-collapsed]')
    .forEach(n => n.setAttribute('data-collapsed', 'false'));
  document.querySelectorAll('section.chapter[data-open]')
    .forEach(n => n.setAttribute('data-open', 'true'));
  document.querySelectorAll('section.chapter > section[data-section]')
    .forEach(n => { n.style.contentVisibility = 'visible'; });  // UX-399 defers layout off-screen
  return document.body.innerText.match(/\\bUX-\\d+\\b/g) || [];
})()"""
```

Before this item's fixes: `closed` (page as loaded) read 0 - every hit
was behind a closed chapter or `.description` door; `opened` (every
door/chapter forced, `content-visibility` lifted so `innerText` sees
what a reader who expands the report does) read **9**:
`UX-478×2, UX-345, UX-477, UX-341×3, UX-09, UX-15, UX-378, UX-344`,
plus `pipe` (`/[\w.-]+\|[A-Z]+\|[A-Z]+\|\d+/`) = 2 on the erased-span
fixture. Source: `bga/correlate.py:1181`'s caveat; `dependency_stages`/
`widest_stage`/`chain_share_of`/`occupancy_share`/`cores_busy`/
`builders_change` (`bga/schemas.py`); `UNMODELED_AXIS_CLAUSE`, the
oversub branch and the skip-clause (`bga/analyzer.py`); the
`utilization_envelope` absence string; `duration_resolution.tasks`
rendered verbatim by `structured.js`'s `INLINE_LIST`.

**Close measured**, same command, same fixture, current commit:
`closed: 0, opened: 0` on both the 1,202-element export and the
erased-span fixture. `dt[data-key="tasks"] + dd` reads
`all.bst · FETCH`. The prior report's "5 remaining" was measured on an
export the fix had not yet reached (`UX-341`/`UX-09`/`UX-15`/`UX-378`/
`UX-344` above) - now fixed, not a live gap.

**The sweep.** `grep -n "(UX-[0-9]*)" bga/*.py` drove a second pass:
an AST walk (`ast.parse`) marks every hit inside a
module/function/class's first `Expr` `Constant` string (a docstring);
a hit whose stripped line starts with `#` is a comment; every other
hit is a candidate, checked for its actual renderer (schema
`description`, an f-string reaching a finding/CLI print, argparse
`help=`) before editing. The 48 hits matching the acceptance pattern
are fixed. Two do not classify as docstring/comment and stay:
`bga/cli.py:2439` (the checkout-mismatch warning -
`test_a_shadowed_checkout_warns_at_startup.py` asserts `"UX-728" in
stderr`; a dev/tooling diagnostic, not a report reader) and
`bga/plane2.py:97` (a trailing same-line comment `startswith` misses).

**Mutation table.**

| instrument | mutation | reddened | count |
|---|---|---|---|
| `re.findall(r"\bUX-\d+\b", caveat)` on `compute_capacity_recommendation`'s output | restore `(UX-14)` | `['UX-14']` | 1 |
| same regex, 3 schema descriptions | restore `` (`UX-478`) `` on `dependency_stages` | `['UX-478']` | 1 |
| node + `dom_shim.mjs`, `format.itemsAsShown` | `if (hint[KEYED_BY]!==KEYED_BY_TASK_UID) return null` → `if (true) return null` | `structured.js`'s `?? value` fallback surfaces the raw join key | 1 |

`test_capacity_recommendation.py`'s existing assertion (the literal
`"(UX-14)"` substring) does not discriminate the id's removal alone
(remaining check is a superset substring) - the regex instrument is
what falsifies. Four more guards had the same shape (an id substring
asserted where a content phrase was the actual claim) and are updated
to the content: `test_the_band_refusal_names_the_run_mode_check`,
`test_the_published_document_carries_that_distinction`,
`test_the_schema_declares_it`, `test_the_page_carries_the_bands_reason`.
Two committed exports refreshed via `dev_refresh_analysis.py --write`,
text-only by `git diff`.

Surfaces: eleven `bga/*.py` modules, `bga/viewer/{format,structured}.js`,
five test files, two golden fixtures, `docs/guides/cli.md`; the touching
sweep 5619 passed, `make lint` clean.

**Deviation.** One HOLD (`findings.py` untouched, four sentences of
48), then the full sweep; the Acceptance Test named `UX-824`'s guard
and was rewritten to the grep and the browser count.
