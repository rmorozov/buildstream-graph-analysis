# UX-445: the track bound is one sample, and nothing has measured the cost it stands for

**Priority:** Medium | **Status:** ⚪ Blocked / Deferred | **Found by:** round 70, setting `TRACE_TRACK_BUDGET` in `UX-430` | **Serves:** anyone whose capture the handoff refuses, and the round that has to decide whether it was right to | **Topic:** guards

## Motivation

`UX-430` gave the handoff a bound in the unit Perfetto actually spends:

```python
TRACE_TRACK_BUDGET = 8_000
```

Everything around it is measured. The track count at 1,202 elements is
16,832 against 15,628 slices and 486 KB, so the byte bound first bites
at roughly nine times the population that already froze a UI; `--planes
1` is a fourteenfold reduction on the same run. Those are real numbers
from a reproducible fixture.

**The 8,000 is not.** It is sized under the one population a field
report described as freezing, and that report is a single sample with no
timing in it. Nothing in this repository has measured what Perfetto
costs per track, so the bound stands for a claim nobody has tested:
that somewhere between one thousand and sixteen thousand rows the
handoff stops being worth offering.

That is the shape `UX-420` paid three red CI rounds for — a constant
sized from one excursion — and it is recorded here rather than hidden in
a docstring, because the docstring is where the last one hid.

## Required Fix

- **Measure the drawing cost against the track count.** Perfetto's UI
  in a headless Chromium, the same trace rendered at several
  populations (`tests/pages.py::scale_two_plane_snapshot` takes a
  `per_element`), and time to interactive for each. A curve, not a
  point.
- **Re-set `TRACE_TRACK_BUDGET` from it**, or delete it if the curve
  says the count is not what costs.
- **Say what was measured and on what**, since a browser benchmark is a
  machine-dependent number and this repository has been wrong about
  exactly that before (`UX-418`: per-file seconds from another runner
  cannot be compared in any form).

## Out of Scope

- **The narrowing controls** — `--planes 1` and `--only-element` are
  `UX-430`'s and are worth having whatever the curve says.
- **Filing a bug against Perfetto**: `UX-430`'s Out of Scope, unchanged.
- **Merging pids onto one track per element**: still its own item, for
  the reason `UX-430` gives — it changes what the trace means.

## Acceptance Test

A pasted table of track count against time-to-interactive on one named
machine and browser build, at three or more populations, and
`TRACE_TRACK_BUDGET` set from it with the reasoning in its docstring
replacing the single-sample admission that is there now.

## Outcome (round 71, 2026-08-31) — ⚪ Blocked, with half of it measured

### What was blocked, and the probe that says so

The item asks for **time-to-interactive against track count in
Perfetto's UI**. That needs the UI, and the environment round 71 was
worked in cannot reach it:

```console
$ curl -sS -o /dev/null -w "%{http_code}\n" --max-time 30 https://ui.perfetto.dev/
curl: (56) CONNECT tunnel failed, response 403
000

$ for h in ui.perfetto.dev storage.googleapis.com github.com \
           registry.npmjs.org cdnjs.cloudflare.com; do ...
ui.perfetto.dev       -> 000
storage.googleapis.com -> 400
github.com            -> 400
registry.npmjs.org    -> 200
cdnjs.cloudflare.com  -> 000
```

`registry.npmjs.org` is the one host the egress policy admits, and
Perfetto publishes neither its UI nor its trace processor there
(`@perfetto/trace_processor`, `trace_processor`: *Not found*;
`perfetto-ui`: a security holding package). `trace_processor_shell` is
not installed either, and it is the query engine rather than the
renderer in any case.

**So `TRACE_TRACK_BUDGET` is left exactly where it was.** Sizing it
from anything measurable here would be a real number, honestly
obtained, measuring a different thing - which is the §5 defect this
item exists to prevent, one round after `UX-430` recorded committing
it. A guessed replacement would be worse than the admitted guess.

### What *was* measured: the emitter's curve

The item asked for "a curve, not a point", and half of that curve is
this repository's own and needs no browser. Four process densities on
the seeded scale run (`tests/pages.py::scale_two_plane_snapshot`,
1,202 elements, this machine):

```text
  per element   tracks   slices     bytes   render s   --planes 1
            1    3,610    2,406   138,489        0.3        1,205
            4    7,216    6,012   240,398        0.6        1,205
           12   16,832   15,628   491,397        1.4        1,205
           24   31,256   30,052   865,529        2.5        1,205
```

Two facts `UX-430` could not state from its single point:

- **`tracks = 2,407 + 1,202 x per_element`, exactly, at all four.** The
  quantity the bound is a threshold on is a straight line in the
  process population, so a threshold is the right *shape* of control
  even though its value is unmeasured.
- **Plane 1's own track count does not move at all.** `--planes 1` is
  a 3.0x reduction at one process an element and **25.9x** at
  twenty-four - `UX-430` recorded "fourteenfold" from the twelve-process
  fixture and read it as a constant. The narrowing control gets better
  exactly where a reader needs it most, and that is now the recorded
  reason to reach for it.

The byte bound still never bites: 865 KB at twenty-four processes an
element is a fifth of `TRACE_BUDGET_B`, at double the density that
already produced the field report.

`TestTheCostModelIsLinearAndNotFittedAtOnePoint` holds the line at two
densities. Two rather than four, because the identity is what is being
checked and a third and fourth fixture cost seconds without changing
what a red would mean.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| D1 | the thread-track opener counts twice | both `test_the_identity_holds_at_another_density[1]` and `[8]`, plus three pre-existing clauses (5 failed, 8 passed) |
| D2 | `--planes 1` stops dropping the process lanes | `..._another_density[8]` and three `TestTheReaderCanAskForLess` clauses (5 failed, 2 passed) |

D2 leaves `[1]` green, and that is the measurement working rather than
a gap: at one process an element the two planes' track counts are close
enough that dropping the lanes is within the fixture's noise floor for
that clause - which is exactly why the density is parametrised.

### What is left, and for whom

The item stays open. What it needs is one run of its Acceptance Test on
a machine that can open `ui.perfetto.dev` in a headless Chromium: the
same trace at the four densities above, time to interactive for each,
the machine and browser build named. Everything else it asked for is
done, and the four traces are one `scale_two_plane_snapshot` call away.

### Deviation from the Required Fix

- **Bullet 1, half done**: the cost curve is measured for what `bga`
  emits and not for what Perfetto draws, for the reason above.
- **Bullet 2, not done**: `TRACE_TRACK_BUDGET` is unchanged and not
  deleted. The curve says the count *is* what grows, so deleting it on
  this evidence would be as unfounded as re-setting it.
- **Bullet 3, done**: the machine and the fixture are named beside every
  figure, in the constant's own docstring where the next round will
  read it.
