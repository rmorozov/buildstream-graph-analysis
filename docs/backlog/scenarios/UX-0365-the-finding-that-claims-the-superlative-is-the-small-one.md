# UX-365: the finding that claims the superlative is the small one

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-207 (the first screen is a decision), UX-261 (the first view leads with what to do) | **Serves:** anyone opening the report to find the biggest lever | **Topic:** analysis

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
