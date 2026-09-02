# UX-533: the served page is the capture-time analysis, and cannot say so

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-296 (the rule that the view parses nothing), UX-389 and UX-407 (payload added since, with no refresh path) | **Serves:** anyone reading a run captured by an older `bga` | **Topic:** viewer

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
