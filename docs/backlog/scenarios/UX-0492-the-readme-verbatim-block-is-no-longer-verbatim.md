# UX-492: the README's "verbatim" real-project block prints a sentence the tool can no longer produce

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-475` changed the sentence | **Found by:** architecture review 10 | **Serves:** the outside reader whose first sight of `bga` is a block that says "verbatim" and is not | **Topic:** docs

## Motivation

`README.md`'s **On a real project** section introduces its block as

> Below is `bga analyze` on a real 3614-second `freedesktop-sdk` build
> (4-core runner, `--builders 4 --max-jobs 4`), **verbatim**

and the block contains, at `README.md:170`:

```text
    Note: 77% of elements have zero slack - this graph is a mesh of near-equal chains, so
    savings on one element are often capped by the next chain rather than by its own duration
```

`UX-475` closed this round and changed that sentence. Today
`bga/findings.py` can emit exactly two things in that slot, and neither
is the line above:

```python
f"Note: {density:.0%} of elements have zero slack, "
f"{off_path} of them off the critical path - this graph is "
"a mesh of near-equal chains, so savings on one element are "
"often capped by the next chain rather than by its own duration"
```

```python
f"Note: {density:.0%} of elements have zero slack, all on "
"the critical path - no second chain of equal length, so a "
"saving on any of them is worth its own duration"
```

`UX-326` made the tool's printed sentences contracts. This is one of
them, quoted in the front door as evidence, and it is stale — the
`UX-132` defect in the file an outside reader meets first. `UX-331` is
the precedent: the README excerpt drifting from what the tool prints.

Two things make it worse than an ordinary stale quote:

- The block says **verbatim**, which is a claim about provenance, not
  a hedge. A reader who diffs it against their own run finds the tool
  wrong rather than the document.
- The build it came from is a real 3614-second `freedesktop-sdk` run
  that no guard can re-run, which is why nothing caught it and why the
  fix has to decide what a stale-but-unreproducible sample is for.

## Required Fix

- The block prints what today's code prints, or the section says
  plainly which release produced it and stops claiming to be current.
- Whichever is chosen, the *rest* of the block is checked against the
  same standard in the same pass — this review checked one sentence,
  not fifty lines.
- If the answer is "re-run it", the run has to be a real one; a
  synthesized stand-in relabelled as freedesktop-sdk would be worse
  than the stale line.

## Out of Scope

- `docs/backlog/scenarios/UX-0075-*.md` and `UX-0076-*.md`, which
  quote the same old sentence inside closed Outcome sections. Those
  are history and are correct as history — fixing guide §3.6 is about
  a *figure a document presents as current*, and an Outcome does not.
- `docs/audits/planted-defect-walk-round-72.md`, which quotes the line
  as the defect it was reporting — also history, and `UX-475` is the
  row that acted on it.
- Whether `mesh-graph` or `chain-graph` is the right verdict for that
  build: `UX-475` settled the rule, and this row is about the document.

## Acceptance Test

```bash
grep -n "zero slack" README.md
```

showing a line that today's `bga/findings.py` can produce, with the
command and run that produced it named; or a README that no longer
claims the block is current output.

## Outcome

**Round 75, 2026-09-02.** A parallel `implementer` track; merged here.

**Which branch, and why.** The round recorded the gap before the work
started: re-running the capture needs a 3614-second build neither this
container nor CI can perform, so the fix is the second branch the
Required Fix names. Nothing below is a synthesized stand-in — every
restored line is quoted from the *same run's* fuller block in
`docs/guides/real-project.md`:415-432.

**The archaeology.** `git log --follow -p -- README.md` reaches six
commits; the history is truncated at root `bc15935`, which added
`README.md` whole, so the commit that introduced the block is not in
it. What the history does show is `717f734` (`UX-365`) hand-patching
one label *inside* the block:

```diff
-  Biggest Opportunity: this build is execution-bound - no wait category
+  Biggest wait category: this build is execution-bound - no wait category
```

So the block is a hand-patched relic, not a re-render. The run itself
is recoverable from this repository's own records and that is what the
README now names: capture run `32064333551`, `freedesktop-sdk` at
`953683fb`, ref `captures/fdsdk/953683fb-incremental-b4j4-32064333551`,
header timestamp 2026-08-17 20:15:03 UTC, wall clock 3614.22s.

**The rest of the block, checked — the half the review skipped.**
Sixteen rows audited against the emitter. Four sentences were **missing
and have been restored** (`-> these elements must get faster…`,
`- the last of those leaves 72%…`, the truncated `Waiting off the
critical path` title, the `(structural projections…)` note); the
ordered list had its uids **shortened to basenames** and now carries
what the emitter prints; three findings the block predates entirely
(`UX-207`'s headline, `UX-478`, `UX-479`) and everything below Key
Findings are now marked `[... elided ...]` rather than cut silently.
One line — the `Note: 77% of elements have zero slack …` mesh sentence
— **no emitter can produce today**: both branches now append
`, N of them off the critical path` or `, all on the critical path`.
It is kept, dated, and named in the new intro, which also says the
block is wrapped to the page width rather than emitter output.

**Mutations.** `PYTHONDONTWRITEBYTECODE=1`; clean re-run 6 passed.

| # | mutation | reddened | count |
|---|---|---|---|
| 1 | intro says "cut where marked, verbatim" | `..._does_not_call_the_block_verbatim` | 1 failed, 5 passed |
| 2 | the `Note:` line replaced with today's mesh sentence | `..._one_no_emitter_can_produce` | 1 failed, 5 passed |
| 3 | linked run id changed, ref left alone | `..._are_the_same_run` | 1 failed, 5 passed |
| 4 | `captured 2026-08-17 by run` → `captured by run` | `..._and_the_day_it_ran` | 1 failed, 5 passed |
| 5 | `UX-475` → `UX-9475` | `..._is_a_task_that_exists` | 1 failed, 5 passed |
| 6 | `_normalise` truncated at `"zero slack"` | 2 clauses | 2 failed, 4 passed |

**Deviation from the Required Fix: one, and it is the finding.** The
Decomposition named three existing guards; **none of them reads this
section** — `test_the_readme_block_is_the_real_output.py` indexes from
`## Quick start`, `test_the_front_door_is_current.py` checks subcommand
and schema inventories, `test_docs_examples.py` runs the Quick start
command. So `test_the_real_project_block_is_dated.py` is new, and the
round's declared guard list asserted a coverage that did not exist.
(`test_capture_ref_patterns.py` *did* pick the new ref token up on its
own, and is not duplicated.) The README is now 323 lines and `UX-135`'s
budget annotation states it.

**Debt filed, not fixed:** `docs/guides/real-project.md` carries the
same retired `Note:` line, the pre-`UX-365` label, prose teaching the
retired reading as current, and an appendix asserting the figures are
"analysed with the current code" — `UX-511`, §3.11.

**Tier.** New file, 0.59s, two `bga analyze` subprocesses — small by
default, no `tiers.py` row.
