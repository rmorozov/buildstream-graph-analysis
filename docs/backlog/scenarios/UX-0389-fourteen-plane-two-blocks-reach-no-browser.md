# UX-389: fourteen of twenty-five Plane 2 blocks reach no browser

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-383 (Plane 2's per-element blocks reach the page), UX-386 (`plane2/v3` is described as what it is), UX-382 (the element placement rule), UX-329 (the terminal and the viewer disagree about Plane 2) | **Serves:** anyone asking in a browser whether the instrument saw everything | **Topic:** viewer | **Area:** bga

## Motivation

The user asked, in as many words, whether all the captured data is
really accessible through `bga view` or Perfetto. Counted against a
real all-planes capture of `examples/06-macro-micro-optimization`:

```text
plane2 blocks in the capture            25
  a key in analyze/v4                    6
  reaching the page through the join     6
  terminal only                         14
```

Six of twenty-five reach a reader in a browser. `UX-383` moved three
blocks one round ago and `UX-385` added `commands_not_observed` in the
same round, which is already the fifteenth terminal-only block — the
gap grows every time the capture learns something new, because
nothing holds the two ends together.

The fourteen are not leftovers. They are the *did the instrument see
everything* questions:

```text
static_census        which elements could be hiding a static binary
spine_policy         whether the ptrace spine ran, and why
max_concurrency      the peak parallelism the hook observed
process_count        how many processes were traced at all
wall_span_s          the window the hook was actually watching
stream_coverage      which of the two streams saw which process
```

A reader in a browser sees a per-element attribution table and has no
way to learn that the spine never ran, so the numbers under it are a
floor rather than a measurement. That is `UX-107`'s rule again, one
level up: the page cannot say "nobody could look" because the block
that knows is at a terminal.

`UX-386` established the shape these live in — 3 of 24 blocks are
keyed by element and the rest are run-level — so `UX-382`'s placement
rule already answers *where* each one goes. What is missing is the
carry from `plane2/v3` into `analyze/v4` and a guard that notices the
next block that does not make the trip.

## Required Fix

- **Every `plane2/v3` block has a declared destination.** Either a
  named key in `analyze/v4` (run-level blocks) or a field on the
  `element_join` row (per-element ones, by `UX-382`'s rule), or an
  explicit, reasoned entry saying it is terminal-only and why. The
  three states are the point: silence is what produced fourteen.
- **The coverage blocks reach the page first**, because they change
  how every other number is read: `spine_policy`, `stream_coverage`,
  `process_count`, `wall_span_s`, `static_census`, `max_concurrency`.
  They belong with the capture's own identity block, not scattered
  through the findings.
- **A guard walks `plane2/v3`'s own block list** and fails on a block
  with no destination — so the next `commands_not_observed` cannot be
  added and quietly stay at the terminal.

## Falsification

The guard above, run against the committed Plane 2 fixture: every
top-level block of `plane2/v3` resolves to a payload key, a join
field, or a declared terminal-only entry, and the declared entries are
enumerated rather than a wildcard. Today fourteen resolve to nothing.

The other direction: adding these must not publish the same population
twice (`UX-288`) and must not move a per-element block to a run-level
key. `UX-386`'s ratio — three keyed by element, the rest run-level —
is the arbiter, and it is already guarded.

## Out of Scope

- Rendering each block well. This item is about the carry and the
  guard; how `stream_coverage` should be *drawn* is `UX-396`'s
  question.
- Plane 1 blocks. The count above is Plane 2's; whether the scheduler
  log has the same gap was not measured this round.

## Outcome (round 64, 2026-08-29) — 🟢 Done

### The gap, measured

The committed two-plane fixture, counted the way the filing counted its
capture:

```console
$ python3 -c "
import json
rep = json.load(open('tests/fixtures/macro_micro/plane2.json'))
pay = json.load(open('/tmp/analyze.json'))
print('plane2 blocks           ', len(rep))
print('  a key in analyze/v4   ', len([k for k in rep if k in pay]))
"
plane2 blocks            24
  a key in analyze/v4     5
```

Five of twenty-four. The nineteen included every *did the instrument
see everything* question — `spine_policy` said `policy: off` on this
very fixture, so every CPU figure the page draws under it is the hook's
floor, and a reader in a browser had no way to learn that.

### After

```console
$ PYTHONPATH=. python3 -m bga.cli analyze tests/fixtures/macro_micro/run \
    --format json | python3 -c \
    'import json,sys; c=json.load(sys.stdin)["plane2_coverage"]
     print({k: c[k] for k in ("process_count","max_concurrency",
                              "wall_span_us","spine_policy")})'
{'process_count': 813, 'max_concurrency': 20, 'wall_span_us': 43508243,
 'spine_policy': {'policy': 'off', 'sandboxes': 9, 'spine_traced': 0}}
```

And on the exported page, in the section a reader already opens to ask
how much of the build Plane 2 saw:

```text
How much did Plane 2 see?   plane2_coverage
  ...
  Spine policy ?    Policy off   Sandboxes 9   Spine traced 0
     Whether the ptrace spine ran, and over how many sandboxes. With
     `policy: off` every CPU figure below is the hook's alone, which
     is a floor.
  Process count ?   813
  Max concurrency ? 20
  Wall span ?       43.5 s
```

### Three destinations, and silence is not one of them

`bga/plane2.py` now carries `DESTINATIONS`: every top-level block of a
`plane2/v3` report declares a key of `analyze/v4`, a field on an
`element_join` row (`UX-382`'s rule), or **terminal-only with the
reason written down**. Eight are terminal-only and each says why; the
six the Required Fix puts first travel in `plane2_coverage` rather than
in six sections of their own, because that is the block whose question
they answer.

`test_every_plane2_block_has_a_destination.py` reads the blocks off a
*committed report* rather than off the inventory, so the next block the
capture learns to write arrives with no entry and fails — which is what
`commands_not_observed` did silently one round ago.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it. B4's
row first claimed `UX-288`'s own sweep went red beside it; run, it did
not - `static_census.per_element` is keyed by twelve elements against
the eleven `element_durations` names, so the sets differ and no clash
is reported. The reason for leaving the map behind is the byte cost
and the duplication, not a guard that catches it.

| # | mutation | reddened |
|---|---|---|
| B1 | stop copying the coverage additions in `bga/cli.py` | 4 of 12, incl. `test_they_are_in_the_coverage_block` and `test_every_payload_destination_resolves` |
| B2 | drop `spine_policy` from `DESTINATIONS` (the "block with no entry" case) | 3 of 12, incl. `test_every_block_the_capture_writes_has_an_entry` |
| B3 | declare `by_element` terminal-only with a three-word reason | 1 of 12: `test_a_terminal_only_block_carries_its_reason` |
| B4 | keep `static_census.per_element` on the way in | 1 of 12: `test_the_census_leaves_its_per_element_working_behind` |

### Deviation from the Required Fix

- **The count in the filing is 25 and the committed fixture has 24.**
  The filing counted a live capture of `examples/06`, which is not in
  the tree; this closes against `tests/fixtures/macro_micro/plane2.json`
  and its 24, plus `resource_pressure`, which is declared and absent
  because the fixture predates `UX-379`'s rusage fields. The guard
  names that one exception rather than wildcarding it.
- **`wall_span_s` is renamed to `wall_span_us` on the way in, and
  converted.** The payload has one unit for a duration; a key spelling
  `_s` beside neighbours spelling `_us` is what `UX-351` is about. The
  Plane 2 report is unchanged.
- **`static_census` is carried without its `per_element` map.** That
  map is one bookkeeping record per element — the census's working, and
  a second copy of the element population, which `UX-288`'s sweep says
  needs a reason. `elements_at_risk` is what the block exists to say.
- **Rendering is untouched**, as the Out of Scope asks: the six blocks
  draw through the machinery that was already there, and the export
  grew by 0 B of source.
