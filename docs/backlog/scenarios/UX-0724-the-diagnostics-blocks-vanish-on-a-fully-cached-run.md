# UX-724: the diagnostics blocks vanish on a fully cached run

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-388 (empty is rendered, absent is not) | **Serves:** R2 and R3, reading an incremental run's report | **Topic:** analysis | **Shape:** judgement | **Area:** bga/diagnostics

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
