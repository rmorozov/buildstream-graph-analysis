# UX-330: the stranger needs a seed

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-213 (the committed-capture precedent), UX-188 (the timeline this makes reachable) | **Serves:** R1 — the evaluating newcomer | **Topic:** docs

## Motivation

Three walk frictions with one root: a no-bst newcomer has no
committed path into half the tool. The example `.bga` stores are
empty scaffolds (a `.gitignore` and `tmp/`), so every store
command dead-ends in "take a snapshot" — with the command that
crashes without bst (UX-324); the only real run data hides in a
fixtures directory named only by real-project.md's *appendix*; no
committed artifact anywhere can feed `bga timeline` ("one trace,
both planes" is untestable by a stranger, and its error on the
seeded snapshot mis-advises "try its parent" — the real cause, no
build.log kept, is never named); and `bga capture report` refuses
the committed plane2/v2 fixture with a message claiming the file
is not what it demonstrably is (`correlate` reads it happily).

## Required Fix

One documented no-bst seed path from the README: a command
(`gen-synthetic` extended, or a documented fixture copy) that
plants a store with at least two runs, a plane2 report **and a
timeline-capable raw log**, so list/aliases/analyze/compare/view/
timeline/whatif/blast all exercise end to end; `timeline`'s
missing-input error names the actual missing file; `capture
report` reads plane2/v2 (or names the version split honestly
instead of "neither").

## Out of Scope

- Committing large captures (the seed is generated or tiny — the
  UX-213 size argument stands).

## Acceptance Test

On a bst-less machine, following the README's no-bst paragraph
verbatim reaches a served `bga view` and a rendered `bga
timeline` with zero errors (walked in CI's installed-mode job);
`timeline`'s error on a log-less snapshot names build.log;
`capture report` on the committed plane2/v2 fixture renders
(mutation: re-refuse → red).

## Outcome (round 50, 2026-08-27) — 🟢 Done

### The gap, measured

```text
$ ls examples/*/.bga/runs
(empty)
$ bga snapshot --list        # in any example project
No snapshots yet. Take one with `bga snapshot -- bst build ...`
```

That command is the one that cannot run without BuildStream. The
only real run data in the tree sat in a fixtures directory named by
`real-project.md`'s **appendix**, and nothing committed anywhere could
feed `bga timeline`, so `UX-188`'s *"one trace, both planes"* was a
claim a stranger had no way to check.

### After

```text
$ bga gen-synthetic --store /tmp/bga-demo
Wrote a store at /tmp/bga-demo
  snapshot: 20260302T091500Z
  snapshot: 20260303T091500Z

$ cd /tmp/bga-demo
$ bga snapshot --list
2 snapshot(s):
  20260302T091500Z      12.4K  @prev
  20260303T091500Z      12.4K  @last

$ bga timeline @last -o t.gz
Wrote both planes to t.gz, aligned on layer02/mod001.bst.
  30 slices on 46 tracks.
```

`analyze`, `compare`, `blast` and `view --export` answer on it too; the
guard runs all six rather than asserting the files exist, because the
failure this item is about is a command that dead-ends, not a file that
is missing.

The seed plants a `project.conf` (store resolution walks up for one),
two snapshots a day apart, and per snapshot a wrapped log, Plane 2
records and a `sources/v1` inventory. The second run's slowest element
is 1.6x slower on purpose: a store whose two runs are identical makes
`compare` correct and useless.

### Two error messages that asserted a cause they could not know

**`bga timeline`** had one sentence for three situations:

```text
<path>: no build.log here. `bga timeline` renders a snapshot directory
(the one `bga snapshot` created), not a run directory - try its parent.
```

Right for a run directory. Useless for a snapshot that kept no wrapped
log - it sends the reader **up** to a directory with no snapshot in it,
and the real cause is never named. Three cases now, each naming its own
remedy; the middle one is the one this item's own seed work hit, on the
first `--store` draft that had no `build.log` in it.

**`bga capture report`** could not open a gzipped raw log:

```text
$ bga capture report examples/06-.../plane2.log.gz
Error: ...no trace events could be parsed from this file... this error
means the file is neither.
```

It is a raw trace. It is gzipped. Every snapshot stores
`plane2.log.gz` (the capture writes it compressed, and `timeline` and
`correlate` both read it that way), so the one command that could not
was the one whose message said the file was not what it is. Detected by magic number
rather than extension, so a renamed file gets the same answer.

**A correction CI made, and this container could not.** The first
draft called `examples/06`'s 813-process capture *"the committed
capture"* and leaned on it as the reproduction. It is **not
committed**: `UX-189` keeps the capture archive out of a clone on
purpose, and this container has it only because earlier work fetched
it. `git ls-files` on that path returns nothing. What caught it was
the skip census (`UX-235`) refusing a skip reason nobody had declared:
the clause reached CI, found no capture, skipped, and the census
failed the run rather than letting a green pass hide it. The two
clauses that read it now declare their absence through the reason
`tests/conftest.py` already knows, and a third clause asserts the same
answer on the **seed's** log, which every clone has.

**A correction to the filing.** It located this defect in "the
committed plane2/v2 fixture", i.e. `plane2.json`. That document reads
fine, and did before this round - measured on both committed plane2
JSON files and on one stamped `plane2/v2` by hand, all exit 0. The
document that was refused is the `.log.gz` beside it.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| M1 | open the raw log as plain text again - re-refuse the gzip | 3 failed, 11 passed, on the seed's own log and on `examples/06`'s where it is present |
| M2 | write the seed's Plane 2 fields as `element` before `ts` | 3 failed, 11 passed: the record parse, the timeline's two planes, and `capture report` |
| M3 | one cache key (`aaaaaaaa`) for every element in the wrapped log | 1 failed, 13 passed: `1 == 14` spans |
| M4 | collapse the three missing-log messages back into one | 3 failed, 1 passed - the fourth clause is the positive control that the three are *different*, which is what M4 is |

M2 and M3 are not hypotheticals: they are the two defects the first
draft of this seed actually had, both found by walking it rather than
by inspecting it. A Plane 2 log with its fields in the wrong order
reads correctly and parses to **nothing**; one cache key for every
element turns fourteen spans into three. Both are recorded in the
guard's docstring.

### Deviation from the Required Fix

- The Required Fix offered *"`gen-synthetic` extended, or a documented
  fixture copy"*. The first was taken: a copy would have committed
  capture bytes the `UX-213` size argument is against, and a generator
  keeps the seed reproducible from a seed number.
- **The reproduction is not on a committed capture**, because there is
  no committed capture to have it on - see the correction above. The
  clause that runs in every clone is the one on the seed's own gzipped
  log; `examples/06`'s is the corroboration where it exists.
- **The acceptance test asks for the walk in CI's installed-mode job.**
  It is a unit guard here instead. The installed-mode job exists to
  catch what `pip install` breaks (`UX-94`'s `bga._tools` packaging),
  and the seed exercises no packaging surface the sweep does not
  already; adding a second twelve-command walk there would double that
  job's runtime for coverage the guard already gives. Stated rather
  than quietly dropped.
