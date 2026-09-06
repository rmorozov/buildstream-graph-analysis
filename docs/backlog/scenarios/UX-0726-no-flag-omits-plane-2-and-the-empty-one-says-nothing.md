# UX-726: no flag omits Plane 2, and the empty one says nothing

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-388 (the absence vocabulary), UX-723 (which measured it) | **Serves:** anyone who wants a Plane 1 capture, and every reader of a run that has an empty Plane 2 | **Topic:** capture | **Shape:** judgement | **Area:** bga

## Motivation

`bga snapshot` has `--no-trace-opens` and `--trace-spine {off,on,auto}`,
which read like the way to capture Plane 1 alone. They are not.
Measured on a copy of `examples/08-process-storm`, isolated
`XDG_CACHE_HOME`, one cold build:

```text
$ bga snapshot --no-trace-opens --trace-spine=off -- bst build toolchain.bst
Compiling the trace hook...                         (stderr)
exit=0

run 20260906T065704Z holds:  plane2.json  plane2.log.gz  host-samples.jsonl
$ python3 -c "...json.load(open('plane2.json'))..."
schema           plane2/v3
process_count    0
matched_count    0
open_count       0
by_binary entries 0
```

The hook is still compiled and injected. What the flags buy is a
Plane 2 report that is **present and empty**, not one that is absent.
`--no-trace-opens` does drop `plane2-resource.json`; nothing drops
`plane2.json`.

And the analysis is silent about which state it is in:

```text
$ bga analyze <run> --format json | jq '.plane2_absence, .plane2_coverage'
null
null
```

Compare a genuinely absent Plane 2 — reached only through `bga wrap` +
`bga extract`, the older path `cli.md` frames as what `snapshot`
replaced — which `UX-685`'s seed-1 walk measured saying, identically on
three surfaces:

```text
"Plane 2 was not captured for this run, so there is no per-process
 detail. `bga snapshot -- bst build TARGET` captures both planes."
```

So there are **three** states and the vocabulary names two.
`cli.md:129` promises "when Plane 2 is not in a report, the report says
which absence it is"; a present-but-empty Plane 2 is a fourth thing
that promise does not reach, and it is the state the documented flags
actually produce.

## Required Fix

Two halves, and the second is not optional:

1. A capture that records no Plane 2 — whether a new flag, or
   `--trace-spine=off --no-trace-opens` made to mean it. Decide which
   and say why in the Outcome; a flag pair that reads like "off" and
   isn't is the defect, not the absence of a third flag.
2. An empty Plane 2 report says so, in `UX-388`'s vocabulary, on every
   surface: `plane2_absence` distinguishes *never captured* from
   *captured and empty*, and the page and the terminal both render it.

## Out of Scope

- The `wrap`/`extract` path itself, which works and is what `UX-723`'s
  recipe now names for this class.

## Acceptance Test

A capture asking for no Plane 2 writes no `plane2.json`, or writes one
whose `plane2_absence` says *captured and empty*; `bga analyze
--format json` publishes that state rather than `null`, and the page
renders a sentence for it. Mutation: return `null` — the guard reds
naming the state it could not tell apart.
