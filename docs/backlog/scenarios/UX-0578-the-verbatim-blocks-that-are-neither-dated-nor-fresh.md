# UX-578: the verbatim blocks that are neither dated nor fresh

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-139 (verbatim is evidence), UX-511 (the dated block), UX-492 | **Serves:** anyone diffing a guide's output against their own | **Topic:** docs

## Motivation

Five pasted outputs in the guides drifted from the tool without a
label saying so:

```text
cli.md:293-297     bundle --no-plane2       tool now lists "plane2.json, plane2.log.gz" and prints "load it with:"
real-project.md:685 correlate block        starts at PARTIAL ATTRIBUTION; the banner, Run/Instance, memory envelope and
                                            "Restructuring opportunity" precede it in a fresh run — no cut marker
cli.md:658/666 vs :1428 + guide L177        486,167 B and 491 KB for the same 16,832-track seeded trace (UX-430 vs UX-446)
what-the-viewer-answers.md:80               "the declared graph, in `structural`" — analyze/v5 has no such namespace (UX-344)
what-the-viewer-answers.md:41               element_join[].peak_rss_kb — absent on the macro_micro fixture's element_join[0]
```

`test_the_readme_block_is_the_real_output.py` diffs the README's
block against a fresh run; nothing does that for `cli.md` or
`real-project.md`.

## Required Fix

Every ` ```console`/` ```text` block introduced by `$ bga …` in
`docs/guides/` is either diffed against a fresh run on the fixture it
names (the README guard, generalised) or carries the dated
"kept, not current" label with its cuts listed (the `UX-511` shape).
The five above corrected or labelled; the two byte figures reconciled
to one measurement with its round.

## Out of Scope

- Blocks from real projects nobody can re-run (`ci-comment.md:79`) —
  labelled, not diffed.

## Acceptance Test

Mutation: change one line of a diffed block — red; remove a kept
block's label — red.

## Outcome (round 83, 2026-09-03)

### The gap

All five premises hold. Measured:

```console
$ python3 -m bga.cli bundle --export <capture> --no-plane2 -o s.tar.gz
  left out (--no-plane2): plane2.json, plane2.log.gz, plane2-resource.json
  load it with: bga bundle --load s.tar.gz         <- absent from cli.md:295
$ python3 -m bga.cli correlate tests/fixtures/macro_micro/{run,plane2.json}
====... / Two-Plane Correlation / Run: / Instance:      <- all cut, unmarked
Joined ... / Memory envelope: ... / Restructuring opportunity:
$ python3 -m bga.cli analyze tests/fixtures/macro_micro/run --format json
  'structural' in document -> False   (analyze/v5, 51 top-level keys)
  element_join[0] carries peak_rss_bytes, not peak_rss_kb  (UX-341)
```

The two byte figures were three — `cli.md:658` 486,167, `UX-430`'s own
file 486,173, `cli.md:1428` and `bga_view.py:794` 491,397. Re-measured
on `tests/pages.py::scale_two_plane_snapshot`:

```text
                  tracks   slices     bytes
  both planes     16,832   15,628   491,074
```

Tracks and slices repeat exactly; bytes move 2-3 between runs, since the
anchor element's name is written into the trace. One figure, to the
kilobyte, in all three places: **491 KB**.

### The close

`tests/unit/test_a_pasted_guide_block_is_fresh_or_dated.py`, 26 tests,
11.6s single-process (10.84 / 11.55 / 12.45) — `MEDIUM`. Population is
the six `$ bga …` blocks in `docs/guides/`; the branch each took:

```text
KEPT  cli.md:259  :281  :302        bundle --export/--load, on `@last`
KEPT  real-project.md:682           correlate /tmp/run /tmp/plane2.json
DIFF  real-project.md:826  :1081    whatif tests/fixtures/macro_micro/run
```

The correlate block was folded into prompted form to be in the
population at all, and dated from `UX-511`'s record; the three bundle
blocks from `UX-520`'s, 2026-09-02. Each carries `Cuts:`.
`real-project.md:826` moved to the committed fixture — the first branch.

### Mutations

| # | mutation | result |
|---|---|---|
| M1 | one line of a diffed block changed | 2 failed |
| M2 | a kept block's label removed | 3 failed |
| M3 | an elision marker removed from a diffed block | 1 failed |
| M4 | `element_join[].peak_rss_kb` back in the guide | 1 failed |
| M5 | `waited-on-flow` answered with `structural` again | 1 failed |
| M6 | `peak_rss_kb` back in cli.md's correlate table | 1 failed |
| M7 | 486 KB back beside 491 KB | 1 failed |
| M8 | a diffable block labelled as an archive instead | 1 failed |

**Two of mine did not discriminate first time.** M3 passed: adjacency
between pasted lines cannot see a cut *before the first* or *after the
last*, which is the README guard's hole too.
`test_the_ends_of_each_paste_are_declared_too` closed it. M7 passed:
the byte clause was reading my own sentence naming the two old figures
rather than the figures the guide quotes — the falsify skill's "guard
that matches its own explanation". That history moved to this file, and
the clause reads a window anchored on `16,832` and `4 MiB`: three sites,
one value.

### Deviation from the Required Fix

Two additions. `cli.md:985` carried the same retired `peak_rss_kb` — one
word, same guide, fixed and guarded here. And the population is the
*prompted* blocks: seven further `bga` output fences put their command
in a separate `bash` fence and are outside this guard, filed as a row
rather than widened here.
