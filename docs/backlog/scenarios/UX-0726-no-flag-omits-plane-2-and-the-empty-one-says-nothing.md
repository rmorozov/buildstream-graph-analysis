# UX-726: no flag omits Plane 2, and the empty one says nothing

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-388 (the absence vocabulary), UX-723 (which measured it) | **Serves:** anyone who wants a Plane 1 capture, and every reader of a run that has an empty Plane 2 | **Topic:** capture | **Shape:** judgement | **Area:** bga

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

## Outcome

**The gap, measured**, on a copy of `examples/08-process-storm` with an
isolated `XDG_CACHE_HOME`, one cold build per flag set:

```text
flags                                plane2.json  process_count  absence()
--no-trace-opens --trace-spine=off   written                  0  None
--no-inject                          written                  0  None
(none)                               written                >0  None
```

Three flag sets, one outcome: a report that exists, records nothing,
and is reported as *no absence at all*.

**The close, measured.** `absence()` returns a fourth sentence:

```text
$ python3 -c "from bga import plane2; print(plane2.absence(run))"
Plane 2 was captured and recorded no process at all, so there is no
per-process detail. That is what every `bga snapshot` flag that reads
like "off" produces - `--no-inject`, `--no-trace-opens`,
`--trace-spine=off` - and it is also what a hook that failed to attach
looks like. `bga wrap` then `bga extract` captures Plane 1 alone on
purpose.
$ python3 -m pytest tests/unit/test_an_empty_plane_two_says_so.py -q
9 passed in 0.19s
```

**The mutation table.** Six, each reddening a named clause.

| mutation | clause that reds |
|---|---|
| the fourth state is never returned | `..._a_report_that_counted_nothing_is_named` |
| it is returned unconditionally | `..._a_report_with_processes_has_no_absence` **and** `..._a_corrupt_report_is_not_called_empty` |
| it is checked before the raw-log state | `..._a_missing_raw_log_still_wins` |
| a corrupt report is called empty | `..._a_corrupt_report_is_not_called_empty` |
| the sentence stops naming the flags | `..._names_the_flags_that_produce_it` |
| the sentence stops admitting a failed hook looks the same | `..._says_a_failed_hook_looks_the_same` |

**One clause of my own filing was wrong, and the suite found it.**
`UX-727`'s Out of Scope said "retrofitting `round-90.md`, which
predates the skill" — an exclusion with no reason, which
`test_every_out_of_scope_entry_names_a_task_or_states_a_decline` reads
as an idea lost. It states the decline now.

**Two deviations.**

*No flag was added, and the Required Fix's first half is answered by
argument rather than by code.* It asked to decide between a new flag
and making `--trace-spine=off --no-trace-opens` mean it. Both are
wrong. The three flags are orthogonal — opened paths, the ptrace
spine, the argv rewrite — and none of them claims to be "capture
Plane 1 alone"; overloading two of them to mean a third thing is how
`--no-inject` already ended up reading like a capture-mode switch when
`UX-146` built it as a diagnostic. What was missing was not a flag but
a **sentence**: `absence()` modelled three states and reality has four,
and the fourth is what all three flag sets produce. `bga wrap` +
`bga extract` remains the Plane-1-only path and the sentence names it.

*The sentence admits it cannot tell two things apart.* A deliberate
Plane-1 capture and a hook that failed to attach leave an identical
tree, and no flag recorded at capture time distinguishes them here.
Saying so is worth more than a confident sentence that is wrong half
the time; a capture-side record of what was asked for would let a
later item split them, and is not this one.

