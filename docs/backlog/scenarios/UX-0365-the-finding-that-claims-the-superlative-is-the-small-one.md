# UX-365: the finding that claims the superlative is the small one

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-207 (the first screen is a decision), UX-261 (the first view leads with what to do) | **Serves:** anyone opening the report to find the biggest lever | **Topic:** analysis

## Motivation

Walked as an outsider: open the report, read the findings, act on the
first one. `findings` on `tests/fixtures/macro_micro`, in published
order:

```text
 #  severity  id                       what it is worth
 0  info      cache-hit-ratio          "this is the nightly scenario, so a 0%
                                        hit ratio is the intent rather than a
                                        finding"
 1  info      confidence               a score, not an action
 2  high      wait-category            "Biggest Opportunity: 5.9% of wall-clock
                                        is UNTRACKED HEAD (2.72s)"
 3  high      time-concentration       4 elements are 71.9% of the 43.2s path
 5  high      joint-saving             the top 3 are worth 23.1s (50% of build)
```

Two things are wrong and they compound.

**The first two findings are `info`, and the first one says it is not a
finding.** A reader who reads top-down spends their first two entries on
a cache note that disclaims itself and a confidence score.

**The finding that carries the word "Biggest" is the smallest of the
three `high` ones.** `wait-category` claims the superlative at **2.72s /
5.9%**; `joint-saving`, three rows below and claiming nothing, is
**23.1s / 50%** — 8.5x larger. `headline.top_actions` agrees with
`joint-saving`, not with the finding labelled "Biggest":

```text
top_actions: core.bst 12.05s, lib-b.bst 4.0s, lib-d.bst 4.0s
```

**The page's own first screen is right**, which is what makes this a
findings-list defect rather than a page defect. `UX-207`'s decision
chapter opens "What should I do?", then the chain-bound sentence, then
`core.bst saves 12.1 s`. So a reader who trusts the top of the page is
served and a reader who trusts the *findings* is misdirected — and the
findings are what `--format json`, the CI comment and every downstream
consumer read.

## Required Fix

Two separable claims, and the second is the one that matters:

- **A severity ordering that puts action first.** `info` findings that
  disclaim themselves do not open the list. This is an ordering rule in
  `bga/findings.py`, not a rewrite of any finding.
- **"Biggest" is a measured superlative or it is not said.** Either
  `wait-category` earns the word against every other finding's worth, or
  the word moves to whichever finding `headline.top_actions` points at.
  A label that asserts a maximum is a claim, and `UX-326` already says
  the tool's sentences are contracts.

## Falsification

Assert against the payload, not a fixed list: no finding may contain a
superlative ("biggest", "largest", "worst", "top") unless its own worth
is the maximum over the findings that publish one. That reddens on
today's tree at `wait-category` — 2.72s against `joint-saving`'s 23.1s.

And the ordering half: the first finding a reader meets carries a
severity at or above every finding below it, or names an action. The
counter-example is the current `findings[0]`.

## Out of Scope

- The decision chapter, which is already right (`UX-207`, `UX-261`).
- Whether `UNTRACKED HEAD` is worth fixing. It may well be; the defect
  is the claim that it is the biggest thing, not its existence.

## Outcome (round 59, 2026-08-28) — 🟢 Done

### The order

```text
before                          after
#0 info  cache-hit-ratio        #0 high wait-category
#1 info  confidence             #1 high time-concentration
#2 high  wait-category          ...
#5 high  joint-saving           #6 info cache-hit-ratio
                                #7 info confidence
```

**Not a severity sort.** The published order carries decisions a blanket
sort would break, and both are well argued where they live: `UX-54` puts
a failed build first, because a real capture in which all four attempted
elements failed led with *"Efficiency Score: 1.00"* and never mentioned
them; `UX-116` puts the capacity recommendation after the memory
envelope it consumes.

So `_run_scope_findings` splits in two — `_run_blocking_findings` (what
invalidates every number below it) and `_run_context_findings` (what the
run *was*: its mode, its cache, its confidence) — with **no finding
moving between them**. `compute_findings` puts blocking first, then the
actions, then context with the other descriptive findings.

### The superlative

The measurement was never wrong. `wait-category` really is the largest
of the non-execution wait categories — a true superlative over a real
population. The scope was missing, so a claim about one population read
as a claim about the report:

```text
- Biggest Opportunity: 5.9% of wall-clock time is UNTRACKED HEAD (2.72s)
+ Biggest wait category: 5.9% of wall-clock time is UNTRACKED HEAD (2.72s)
```

`execution-bound` carried the same label and moved with it. Nothing else
in the tool claims a maximum.

### What moved with it

- The golden snapshot, regenerated by the `measure` recipe: 54 lines,
  and the diff is exactly the re-worded title, its `copy_text`, and
  `confidence` changing index. Nothing else.
- Two guards quoting the old label (`test_attribution_hints.py`,
  `test_report_key_findings.py`), re-pointed at the new one with the
  reason beside them.
- **The README's pasted block**, which is real output and had
  `Confidence` above the wait-category line. `UX-192`'s guard caught it
  — a block claiming to be verbatim output and drifting from it is
  precisely what that guard exists for, and this is the first time it
  has fired on a deliberate change.

### Mutations

Four against the committed tree, all reverted:

| | mutation | result |
|---|---|---|
| M1 | the superlative loses its scope again | 4 failed |
| M2 | context findings back on top | 5 failed |
| M3 | the scoped superlative deleted rather than scoped | 2 failed |
| M4 | blocking facts demoted below context (breaks `UX-54`) | 6 failed |

M3 is the one that keeps the fix honest: deleting the word is not
scoping it, and the guard says so. M4 reddens six clauses including the
source-level one that reads `compute_findings` — `UX-54` is a rule this
item had to not break, so the guard holds it too.

### Deviation from the Required Fix

The Required Fix asked for "a severity ordering that puts action first".
What landed is narrower and does not re-order by severity at all: the
run's *description* moves below the actions, and everything else keeps
the order its own item argued for. A severity sort would have
re-litigated `UX-54` and `UX-116` silently, which is a bigger change
than this item measured a need for.

The second half — "either `wait-category` earns the word or the word
moves" — landed as a third option the filing did not consider: the word
stays and names its population. That is the cheaper fix and the true
one, since the finding *is* the biggest of something.
