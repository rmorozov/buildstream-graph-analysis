# UX-724: the diagnostics blocks vanish on a fully cached run

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-388 (empty is rendered, absent is not) | **Serves:** R2 and R3, reading an incremental run's report | **Topic:** analysis | **Shape:** judgement | **Area:** bga/diagnostics

## Motivation

Found by `UX-685`'s walk at seed 2 — the empty-population class.
`--diagnostics` was passed on both runs of the same project:

```text
$ python3 -c "... json.load(analyze_prev_diag.json) vs analyze_last_diag.json"
bottleneck       @prev dict   @last NoneType
parallelism      @prev dict   @last NoneType
$ diff <(bga analyze @prev --diagnostics) <(bga analyze @last --diagnostics)
lines 52-60 present on @prev, absent on @last:
  Max Blast Radius / Bottlenecks Identified / Parallelism Profile
```

`@last` is a 100%-cache-hit incremental run: 1 cached, 0 rebuilt. The
Advanced Diagnostics and Structural Analysis blocks do not say they
found nothing — they are **not printed at all**, and no line explains
the difference. A reader who ran the same command twice sees a shorter
report and no reason.

`UX-388` settled this class: *a declared collection with nothing in it
is a population that came back empty, and empty is rendered*. Its fix
and its guard are the **page's**; the text report was never brought
under the rule, and `bga analyze`'s own guide (`cli.md:362`) says the
two formats "cannot disagree".

## Required Fix

The text report's diagnostics blocks render their heading and a
sentence when the run has no rebuilt element, the way the page's
sections do — naming which absence it is: nothing was rebuilt, so
there is no blast radius to rank, rather than the block being gone.
`--format json` publishes the same distinction rather than `null`.

## Out of Scope

- The page — `UX-388` holds it, and the walk confirmed it holds.

## Acceptance Test

On a 0-rebuilt incremental run, `bga analyze --diagnostics` prints the
Advanced Diagnostics heading and a sentence naming the absence, and
`--format json`'s `bottleneck` is a declared-empty shape rather than
`null`. Mutation: return to omitting the block — the guard reds on the
missing heading.

## Outcome (2026-09-06)

### Gap measured

`examples/08-process-storm`, cold then incremental (0 rebuilt), before
the fix:

```text
Advanced Diagnostics:          <- heading present, body empty, no line
                                   (Max Blast Radius / High Criticality gone)
Structural Analysis:           <- heading absent entirely
```

`--format json` (`@last`, before): `bottleneck`/`parallelism`/
`graph_metrics`/`graph_summary`/`sensitivity`/`deferrability`/
`batch_opportunities` all key-absent, matching `ANALYZE_FULL_KEYS`'
own claim that they are "always present" being silently violated.

### Close measured

Same fixture, after:

```text
Advanced Diagnostics:
  Nothing to report here for this run — the analysis ran and found none.

Structural Analysis:
  Nothing to report here for this run — the analysis ran and found none.
```

`--format json` (`@last`, after): all seven keys present, each `{}`;
`jsonschema.validate` against `analyze/v6` still passes (schema already
typed them `["object","null"]`, no `required`, no version bump needed).

Real walk fixture (`examples/06-macro-micro-optimization`,
`test_the_journey_has_an_answer_key.py`):
`pytest ...::test_the_text_report_says_which_absence_it_is` — 1 passed,
72.07s. `make test-touching`: 80 files, 1642 passed, 8 skipped, 99.55s.
`make lint`: clean. `dev_baseline.py --check`: 299, unchanged.

### Mutation table

| # | mutation | reddened | count |
|---|---|---|---|
| A1 | Structural Analysis: restore `and result.structural` truthy gate, drop the empty-branch | `test_the_text_report_says_which_absence_it_is` (`"Structural Analysis:" in warm_text`) | 1 failed |
| A2 | Advanced Diagnostics: drop the `has_ranked_population`/sentence branch | same test, `count("...found none") == 2` | 1 == 2, failed |
| B | `--format json`: restore `and result.structural` truthy gate on `_lift`, drop the declared-empty stand-in | same test, `warm_json.get("bottleneck") == {}` | `None == {}`, failed |

All three reverted from the untouched copy (`falsify` step 1) and
reconfirmed green (1 passed) after each revert.

### Deviations

*The answer-key row was rewritten, not deleted.*
`test_the_text_report_still_drops_its_diagnostics_blocks` recorded this
gap and said in its own docstring that closing it reddens the clause.
It is now `test_the_text_report_says_which_absence_it_is`, asserting
the rule. That is the ratchet `UX-685`'s answer key was built to fire.

*No schema version moved.* `analyze/v6` already types the seven
structural keys `["object","null"]` with no `required`, so `{}`
validates. The track checked rather than assumed, and did not take the
bump decision on its own.

*`bga/report/_shared.py` was not in the declared surface.* The
`UX-388` sentence had to live somewhere both `text.py` and `json.py`
read; `_shared.py`'s own docstring names that as its job. Accepted.

*Friction, filed as `UX-728`:* a track's repro through the `bga`
console script or `python3 -m bga.cli` runs the **session's** checkout,
not the worktree, unless cwd is the worktree or `PYTHONPATH` names it.
The track's first post-fix repro silently ran unpatched code.
