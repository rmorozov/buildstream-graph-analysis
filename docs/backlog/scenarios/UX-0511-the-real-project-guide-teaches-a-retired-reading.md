# UX-511: the guide the README sends readers to teaches a retired reading as current

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-492` (the same block, on the front door) | **Found by:** round 75, auditing `UX-492`'s block line by line | **Serves:** the reader who follows the README's link and gets the same stale output with prose built on it | **Topic:** docs

## Motivation

`UX-492` dated the README's real-project block and named the one
sentence no emitter can produce. The guide it links carries the same
defect and two more:

```text
docs/guides/real-project.md:415-432   the identical retired `Note:` line,
                                      and the pre-UX-365 `Biggest Opportunity`
docs/guides/real-project.md:456-460   prose teaching the retired mesh reading
docs/guides/real-project.md:1018      "analysed with the current code"
```

The last is the worst of the three, because it is a claim about
freshness rather than a stale figure: the appendix asserts the Plane 1
figures are that capture's `run/` directory analysed with the current
code, which `UX-492`'s audit has just shown is false — four sentences
the emitter prints today are absent from the pasted block.

## Required Fix

- The block is dated the way `UX-492` dated the README's, from the same
  capture record, or re-rendered from a run this repository can perform.
- The prose at :456 no longer teaches a reading the emitter retired.
- The appendix's freshness claim is true or is removed. It is one
  sentence and it is the one a reader would rely on.
- Whatever it becomes, a guard reads it — `UX-492` found that none of
  the three guards the round expected to cover its section did.

## Out of Scope

- `README.md`, closed as `UX-492`.
- The capture itself. It is a 3614-second freedesktop-sdk build
  that neither this container nor CI can perform, which is the
  same constraint `UX-492` recorded and worked within.

## Acceptance Test

`git grep -n "zero slack\|Biggest Opportunity" docs/guides` returns
nothing undated, and the appendix sentence pasted with whichever way it
was resolved.

## Outcome (round 76, 2026-09-02)

### The gap

The three lines the Motivation names, plus one the audit did not: the
prose under the block taught `Biggest Opportunity` as the current label,
and so did `docs/guides/cli.md:1870`. `UX-365` scoped it to `Biggest
wait category` and `bga/findings.py` prints only the latter:

```console
$ grep -rn 'Biggest wait category\|Biggest Opportunity' bga/
bga/findings.py:1106:  f"Biggest wait category: this build is execution-bound - "
bga/findings.py:1141:  f"Biggest wait category: {pct:.1f}% of wall-clock time is "
```

### The close

The block is dated from the same capture record `UX-492` used — run
`32064333551`, 2026-08-17, `captures/fdsdk/953683fb-incremental-b4j4-32064333551`
— framed *kept, not current*, with the same five rows listed underneath.
`Biggest Opportunity` is refreshed in place in both blocks and in the
prose; the zero-slack paragraph now teaches the split note and says to
read your own run's, not this one's; the appendix says the figures were
analysed when each block was written and **not** re-run since.

```console
$ git grep -n "zero slack\|Biggest Opportunity" docs/guides
docs/guides/cli.md:307:  | `mesh-graph` | ... and some are off the critical path ... (`UX-475`) |
docs/guides/cli.md:309:  | `chain-graph` | ... all of them are on the critical path ... (`UX-475`) |
docs/guides/real-project.md:432:    Note: 77% of elements have zero slack - ...   <- inside the dated block
docs/guides/real-project.md:445:  scoped `Biggest Opportunity` to `Biggest wait category` — refreshed in
docs/guides/real-project.md:477:  **The `zero slack` note tells you whether the top row is even
```

Nothing undated remains: `cli.md`'s two rows describe the current split,
:432 is inside the dated fence, :445 names the rename as history, :477
is the rewritten prose.

The guard is `UX-492`'s, widened. `test_the_real_project_block_is_dated.py`
now parametrises its two classes over both documents, and gains a clause
for the retired label and two for the appendix's freshness claim.

### Mutations

| # | mutation, on the guide | result |
|---|---|---|
| M1 | the block's date and run link removed | 2 failed |
| M2 | the section calls the block verbatim again | 1 failed |
| M3 | `Biggest Opportunity` back in the block | 1 failed |
| M4 | the appendix claims freshness again | 2 failed |
| M5 | the capture ref names a different run than the link | 1 failed |

### Deviation from the Required Fix

One addition. `docs/guides/cli.md:1870` carried the same retired label
and is outside the file this row names; it is one word, in a guide, and
leaving it would have meant filing a row to change `Opportunity` to
`wait category`. Fixed here and recorded.

Tests: 8 → 16 in `tests/unit/test_the_real_project_block_is_dated.py`.
