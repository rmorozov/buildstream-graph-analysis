---
name: measure
description: The recipes this repository re-derives every round - regenerating the golden snapshot, building the 1,202-element synthetic run, measuring the exported report's size, and re-timing the test tiers. Use when a claim needs a number rather than an adjective.
---

# measure

Every claim here is a pasted measurement (style guide rule 4,
[`docs/contributing/style-guide.md`](../../../docs/contributing/style-guide.md)).
These are the four that get rediscovered from a docstring each round.

## A committed analysis, after a deliberate behaviour change

```bash
python3 tools/dev_refresh_analysis.py            # what disagrees, and how
python3 tools/dev_refresh_analysis.py --write tests/fixtures/with_timeline
git diff tests/fixtures/with_timeline/analyze.json
```

Two fixtures hold an analysis the tool produced — the golden snapshot
and `with_timeline` — and `--write` with no argument refreshes both.
Then read the diff and confirm the change you intended is the *only*
one.

This used to be a shell pipeline here, a second copy in
`tests/test_golden.py`'s docstring and a third in its helper. The
rewrite of the fixture's path and the dropping of `run_instance` and
`producer` are all load-bearing, and the fixture that had no recipe at
all drifted four findings behind the analyzer before anything noticed
(`UX-486`). The rule is stated once now, in the tool, and both guards
call it.

## A run at scale, byte-reproducible

```bash
bga gen-synthetic /tmp/scale --seed 1     # 1,202 elements, deterministic
bga analyze /tmp/scale --diagnostics
```

The seed makes it reproducible across machines, which is what lets one
round's figure be compared with another's. Round 2 found four defects
at this scale that were invisible at eleven elements.

## What the exported report weighs

```bash
bga view /tmp/scale --export /tmp/report.html
wc -c /tmp/report.html
```

Two numbers matter and they are different: the **page** (the
hand-written modules plus the stylesheet) and the **data** (the
embedded JSON). `tests/unit/test_the_report_you_can_attach.py` splits
them by stripping the `<script type="application/json">` blocks. The
backstop on the golden export is a measurement, so when it moves, say
which half moved — a composition guard exists precisely so the ceiling
cannot be raised without one.

## A real capture, with both planes in it

The scale run (`gen-synthetic`) has Plane 1 only — it fabricates a
schedule, not processes. For anything about Plane 2, the sandbox tax,
the process population or the trace's real shape, capture a real build.
`examples/06-macro-micro-optimization` is the one built for it: 11
elements, a deliberate six-deep chain, translation units calibrated to
about a second of real `g++` each.

```bash
cd examples/06-macro-micro-optimization
bga snapshot --project "$PWD" -- bst build all.bst
```

**Three things cost a round each to rediscover:**

- The flag is `--project`, and it wants the project directory. There is
  no `--into`; the store is `<project>/.bga/runs/<stamp>`.
- **A warm build gives you Plane 1 only.** Everything caches, no
  sandbox runs, `plane2.log.gz` comes back at 31 bytes and `bga
  timeline` says *"the Plane 2 capture attributes no span to an
  element"*. That is not a failure — it is the incremental build, and
  it is worth capturing deliberately, because several defects only
  appear there (`UX-431`).
- To get **both** planes, bust the cache first. Copy the project out of
  the tree and change a source in the copy, so the repository stays
  clean:

  ```bash
  cp -r examples/06-macro-micro-optimization /tmp/ex06 && rm -rf /tmp/ex06/.bga
  for f in $(find /tmp/ex06/files/src -name "unit_0.cpp"); do
      echo "// cache-buster $(date +%s)" >> "$f"
  done
  cd /tmp/ex06 && bga snapshot --project "$PWD" -- bst build all.bst
  ```

  Measured that way: 9 elements rebuilt, **813 hook-covered
  processes**, a 311 KB snapshot, about 40 s of wall clock. The 813
  is `UX-123`'s post-collapse figure and nothing since has
  re-measured it — that needs a real `bst` build, so `UX-584` left
  all four alone and said so rather than guessing. **Treat them as
  the shape, not the number**, until a capture round takes them
  again.

Then the trace, and the questions:

```bash
bga timeline /tmp/ex06/.bga/runs/<stamp> -o /tmp/six.pftrace
python tools/dev_perfetto_queries.py /tmp/six.pftrace --fetch
```

**Capture both shapes when the round is about the trace.** The cached
run and the full rebuild disagree about almost everything that matters —
on the same 34-edge graph, one drew 0 arrows and reported 0 dropped,
the other drew 10 and reported 24. A round that measures only the full
rebuild sees a working tool.

## Asking the canned questions of a real trace

```bash
bga timeline /path/to/snapshot -o /tmp/two.pftrace
python tools/dev_perfetto_queries.py /tmp/two.pftrace --fetch
```

Runs all seventeen questions in `bga/viewer/questions.js` against the
trace and says, per question, whether it answered. `--fetch` downloads
the pinned reader if none is on `PATH` — Perfetto's own prebuilt, from
`commondatastorage.googleapis.com` and not `get.perfetto.dev`, which is
a redirector some proxies refuse.

**Do this whenever a round touches the emitter, the annotations or the
library.** `UX-312`'s guard checks the questions name only vocabulary
the trace emits, which runs everywhere and is not the same claim: a
question whose keys all exist still answers nothing if the values are
absent, because `extract_arg` returns null rather than failing. Round
69 ran them for the first time and three came back empty, one of them
the question that resolves the graph's shape.

The gate for this is optional and skips when the reader is missing
(`tests/trace_processor.py`), and it had skipped on every machine this
project ever ran on — so "the suite is green" has never meant these
questions work. `--fetch` exists because that download was the whole
of the friction.

An empty answer and a refused query are different findings, and the
exit code says which: 0 with an `empty:` list means the trace cannot
answer, 1 means a question is malformed.

## Re-timing the tiers

```bash
python3 -m pytest tests/ --durations=0 -q
```

Sum setup+call+teardown per file; a file above `LARGE_FLOOR_S` is
large, above `MEDIUM_FLOOR_S` is medium, and everything else is small
by default. The floors and both lists are in
[`tests/tiers.py`](../../../tests/tiers.py). **A file moves tier when
its measurement moves, not when it feels slower** — re-measure before
editing either list.

Timing the suite itself:

```bash
time make test-small
time make test
```

## When you quote a number

Name the command and the fixture that produced it, in the sentence. "a
33% spread across five captures of the same freedesktop-sdk commit" can
be re-checked in three years; "roughly 5% run-to-run noise" cannot, and
this repository has already been wrong that way — the same list at n=3
supported a 5.8% figure that four documents quoted.

## Before you trust the number: what is it a number *of*?

The instrument is the thing this repository gets wrong most often. A
round-68 sweep of the backlog, the guards and the design documents
found about thirty sightings across about twenty-six items of one
defect — **an instrument reading a proxy rather than the thing it
names**. The fixing guide's §5 states it as a rule; this is where it
gets asked, because the mistake is made while writing the measurement
and is invisible when reading it back.

Three questions, in order:

1. **What quantity does this actually read?** Not what it is called —
   what the code touches. `UX-204`'s page-size guard summed every file
   in `bga/viewer/`, including two an export never carries.
2. **Is that the quantity the name claims?** `UX-296` read
   `ru_maxrss` in a subprocess, which returns the *parent's* high-water
   mark: a 10 MB child reported 411 MB.
3. **At the magnitudes it will see, can it tell the answers apart?**
   A ratio of two hundredth-of-a-second numbers cannot. Measured on two
   runs of this suite at one commit, a file under 0.1s ran **×4.21** its
   own time with nothing changed (`UX-423`).

The four shapes, so you can recognise yours:

| shape | the tell | worked example |
|---|---|---|
| a text scan that cannot tell code from data | a longer regex keeps almost working | `UX-403` |
| a ratio at the noise floor | the operands moved by different factors | `UX-420`, `UX-422` |
| a comparison across machines | "it passed on mine" | `UX-418` |
| the wrong artifact or population | the number is real, its subject is not | `UX-359` |

**A guard you only read is a guard you have not checked.** Every one of
those was found by running something — a mutation, a second machine, a
census — and none by re-reading the code. See the `falsify` skill.
