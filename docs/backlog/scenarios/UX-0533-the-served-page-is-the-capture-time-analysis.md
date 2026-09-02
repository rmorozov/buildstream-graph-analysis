# UX-533: the served page is the capture-time analysis, and cannot say so

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-296 (the rule that the view parses nothing), UX-389 and UX-407 (payload added since, with no refresh path) | **Serves:** anyone reading a run captured by an older `bga` | **Topic:** viewer

## Motivation

The same cold run, opened two ways:

```text
stored analyze.json (bga view <run>)      plane2_coverage 14 terms · 11 findings · no `restructuring`
fresh analysis (analyze.json removed)     plane2_coverage 20 terms · 15 findings · `restructuring` present
missing on the stored page                Spine policy · Process count · Max concurrency · Wall span · Static census · Static binary disclaimer
producer.version                          0.3.0 on both
```

`tools/bga_view.py:306` serves `published_analysis(run) or
_analyze_now(run)`; the snapshot wrote the analysis at capture time
(`bga_snapshot.py:545`), and nothing since — not the producer stamp,
not a contract version — distinguishes "this tool's analysis" from
"the analysis the capturing tool wrote". Every payload key a later
round adds is invisible on every existing run, silently.

## Required Fix

The page states which it is showing ("analysed at capture by 0.3.0;
this tool would add N sections — re-analyse") and `bga view` offers
`--reanalyse` (or does so when the stored producer's contract set is
older than the tool's, `UX-249` already records the set). The
stored file is never overwritten in place without the flag.

## Out of Scope

- Changing what `snapshot` writes — capture-time analysis is right
  for the CI comment; the view's job is to say what it has.

## Acceptance Test

Opening the ex06 cold run with the stored analysis shows the
sentence and the count; with `--reanalyse` the 20 terms render.
Mutation: drop the producer comparison — the sentence disappears,
red.

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

```text
$ git show HEAD:tools/bga_view.py | grep -n 'published_analysis(run) or'
    documents = {"report.json": published_analysis(run) or _analyze_now(run)}
$ git show HEAD:bga/viewer/app.js | grep -c 'analysis'      ->  0
```

On `tests/fixtures/with_timeline`, whose `analyze.json` predates the
producer stamp, the two documents differ and nothing said so:

```text
stored keys 41 · fresh keys 43 · added by this build: producer, run_instance
stored producer: unstamped
```

Two keys on a nearly-current fixture; the item's field case is six page
sections. Either way the page had no word for which document it had.

### After

`analysis_source` in `tools/bga_view.py` answers it from `UX-249`'s
contract set — not a version string, which Direction 10 argues is a
lossy summary of nine contracts, and not a key count, which would call
a run stale for having nothing to put in a section. `analysisSentence`
in `bga/viewer/app.js` spells it on the same line as the producer stamp
— the node probe in the guard, all three notes:

```text
capture, stale     analysed at capture by bga 0.2.9; 1 of the contracts it
                   records have moved since, and 3 of the 35 sections this
                   build always publishes are absent — re-run with
                   `bga view RUN --reanalyse`
capture, current   analysed at capture by bga 0.2.9
--reanalyse        analysed here by bga 0.3.0
```

`--reanalyse` reaches `payloads`, `export` and `serve`. The stored file
is **never written** — with the flag or without it. Overwriting it would
delete the capture-time analysis this item's Out of Scope keeps for the
CI comment, so the guarantee is stronger than the Required Fix asked and
`test_view_never_writes_the_stored_analysis` holds it byte-and-mtime.

The export grew **+1,852 B** on both committed fixtures, +1,096 of page
and +756 of the `run.analysis` note; both bounds still hold, restated
in `tests/unit/test_the_report_you_can_attach.py`.

### Mutations verified red and reverted (6)

| # | mutation | red |
|---|---|---|
| M1 | drop the producer comparison (`stale` always false) | 3 |
| M2 | the sentence is printed whether or not it moved | 1 |
| M3 | count every declared property, not the always-present set | 1 |
| M4 | `payloads` ignores `--reanalyse` | 1 |
| M5 | the view rewrites the stored analysis in place | 1 |
| M6 | the heading computes the sentence and does not draw it | 1 |

### Deviation

The item's sentence sketch says "this tool would add N sections". `N`
cannot be known without running the analysis the sentence exists to
avoid, and the schema's 56 declared properties overstate it by 13 on the
golden run (43 keys fresh, 56 declared). The count published is exact
instead: `ANALYZE_FULL_KEYS` — the sections this build says *every* full
report carries — minus the ones the stored document has.
