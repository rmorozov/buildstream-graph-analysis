# UX-1047: the page's one `h1` is the run, or §6e.1 says it is the wordmark

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §6e.1, §3i, §4f | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

## Motivation

Measured on `main` at `814a2db8` on three pages with **both planes**: `macro_micro` (11 elements), and `bga gen-synthetic <d> --store --seed 1` (`--layers 6 --width 12`, 74 elements; `--layers 20 --width 60`, 1,202) with `bga capture report --json <snapshot>/plane2.log --project-dir <d> > <snapshot>/plane2.json`, each exported by `python3 -m tools.bga_view <snapshot>/run --export` and booted through `tests/browser.py` at 1440x900:

```text
h1#wordmark      "bga"                       21px  (--font-h1)
h2.chapter       "Where did the time go?"    21px  (--font-h1, since UX-1018)
header alias     the run's alias and instant  not a heading
```

§6e.1 (binding): "one outline: one `h1` (the run), `h2` a chapter at
`--font-h1`", and its guard's stated clause is "sizes strictly
decreasing by level". §3i: the header holds "a wordmark on the left,
the run's alias and start instant". The page's `h1` is the product's
name, and it is the same size as every chapter title, so the outline's
top is neither the run nor larger than what it heads. §4f has four
sizes, so an `h1` above `--font-h1` needs a fifth or the chapter
drops a step. The guard does not see it:
`test_the_heading_outline_has_three_levels.py` holds `min(h2) >
max(h3)` and never compares `h1` with `h2` - measured equal on all four
pages at both widths - so it is narrower than the rule it cites.

## Decomposition

Input classes: an aliased run, an unaliased run, the served page's run
switcher, the compact header.

## Required Fix

Decide: (a) the header's run alias is the `h1` and the wordmark is not
a heading — §3i's 72 px holds, and `h1` shares `--font-h1` with the
chapter as the one allowed tie; or (b) §6e.1 names the wordmark and
drops "the run". Default, if no decision: (a). Amend §6e.1, §3i and
§4f to one outline.

## Decision

Route (a), Ruslan's default. The header becomes `<span id="wordmark">bga</span><h1 id="run-name"></h1><p id="run-identity"><span id="run-instant"></span></p>`. The wordmark is text at `--font-small`, not a heading; the h1 stays `--font-h1`, the one allowed tie with h2. `stampIdentity` sets the h1 to `run.name` (snapshot stamp for a stored run, directory basename otherwise, "unnamed run" when run.json is absent); the path `title` moves from `#wordmark` to the h1. The switcher reloads on `?run=<stamp>` and boot re-stamps, so the h1 follows; the @alias stays in the picker's option text.

- Rejected: (b) naming the wordmark in §6e.1 (Ruslan kept the default); a fifth size above `--font-h1` (breaks §4f's four steps); chapter h2 down to `--font-h2` (h3 would need a step below 17px); "(@last)" in the h1 (run.json carries no alias).
- Files: `bga/viewer/index.html`, `style.css` (282-298), `app.js` (75-96 `stampIdentity`), `tools/dev_rendered_strings.py:28` (heading role `h1:not(#run-name),h2,...`: the run name is data, not a label), `docs/design/rendered-strings.json` via `--write`, `tests/unit/test_the_heading_outline_has_three_levels.py`, `tests/unit/test_the_header_keeps_its_budget.py` (43-49, 97-101: the title check moves to the h1), `tests/unit/test_the_page_moves_between_runs.py` (215-224), styleguide lines 70, 1304, 1321-1325, 1784-1788, 1897-1900 (1294 stays: a pre-142 baseline).
- Guard: the outline file gains (1) the one h1's text equals the export's inlined run.json `name`; (2) the h1's computed size is ≥ max(h2) and equals `--font-h1`; (3) `#wordmark` is not h1-h6 and has no `role=heading`. The between-runs file: after `?run=20260101T000000Z` the h1 reads that stamp.
- Mutations: `<h1 id="wordmark">` back with `#run-name` a span reddens (1) and (3); `h1{font-size:var(--font-h2)}` reddens (2); stamping only on first boot reddens the switcher clause.
- Measure: the Outcome pastes the header height at 390x844 before and after (68 px today); it stays ≤ 72 (§3i).
- Class product; one track, bounded, sonnet.

## Out of Scope

The header's budget (§3i) and the picker.

## Acceptance Test

`test_the_heading_outline_has_three_levels.py` reads the `h1`'s text
against the run's alias, and the size clause the rule states.
Mutation: put `h1` back on the wordmark, and the guard reds.

## Outcome

Gap measured (before, golden export, 390x844): header 70px;
`rendered-strings.json` carried `{"exception": "command name", "role":
"heading", "text": "bga"}` from `#wordmark`.

Close measured (after, same fixture/width): header 70px (≤72px §3i);
that row dropped from `rendered-strings.json` (`--write`, -5); h1 text
`run`, 21px, ties `h2`; `#wordmark` has no heading role; the switcher's
served h1 follows the stamp. Round two: `runDisplayName` climbed a
segment whenever `run.name==="run"` - macro_micro via `export_uri`
read h1 "snapshot" (header 93px, over budget). Gated the climb on the
store's stamp pattern (`bga/run_store.py`'s `_STAMP`); gave `#run-name`
`max-width`/ellipsis so an unbounded name can't grow the header either
way (62-char synthetic name: 70px with it, 158px without). Round
three: the pattern missed `new_snapshot_dir`'s `<stamp>-NN`
disambiguator - extended to `/^\d{8}T\d{6}Z(-\d{2})?$/`. Round four:
splitting `#wordmark` out of `h1#wordmark` added a 4th header child,
reddening `test_apparatus_in_its_place.py`'s 3-block budget (§2b) -
`#run-identity` (now a `div`, holding a heading) took the wordmark,
h1 and instant back under one header child; `.claude/skills/derive`'s
worked example left `runDisplayName`/`_STAMP_RE` unplaced, reddening
`dev_js_deps.py --crossings`'s exit - added both to its "app" group,
same crossings. 1169+ tests passed across all four rounds. Four
tree-wide guards clean: `ruff`, `lint-docs`, `dev_baseline.py --check`,
`dev_sizes.py --check`.

Mutation table (rounds 1-3 collapsed; full detail in `git log`):

| mutation | reddened | count |
|---|---|---|
| h1/wordmark markup and size mutations (3, round 1) | outline file's h1/wordmark/tie tests | 3 failed / 11 each |
| `stampIdentity`/`runDisplayName` fallback mutations (2, rounds 1-2) | switcher and outline stamp tests | 1-3 failed |
| `#run-name`'s ellipsis removed (round 2) | `test_a_long_run_name_still_fits_the_budget_on_a_phone` (158px) | 1 failed / 9 |
| `_STAMP_RE` without `-NN` (round 3) | same-second-snapshot test (h1 read "run") | 1 failed / 11 |
| `<span id="wordmark">`/`<h1>` back as separate header children (round 4) | `test_the_header_is_identity_and_fits` both widths (`blocks: 4`) | 2 failed / 19 |
| `runDisplayName`/`_STAMP_RE` removed from the derive skill's "app" group (round 4) | `test_the_derive_skill_s_example_runs` (`UNPLACED`, exit 1) | 1 failed / 20 |

All reverted from the saved pre-mutation copy and reconfirmed green.

Deviation: the switcher mutation (round 1) is not literally "stamping
only on first boot" - a full-reload switcher has no state for a
boot-once flag to keep, so the stamp fallback was dropped instead,
through the code path that runs. Styleguide line 1304 needed no edit -
rule 1 at 1306 already stated route (a).
