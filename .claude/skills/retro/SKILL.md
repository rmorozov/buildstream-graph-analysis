---
name: retro
description: The weekly retro - reads a window's bookkeeping ledger, run ledger and CI history, groups repeated findings by the command that shows them, and proposes the top classes as optimization rows for the architect. Use when a week has passed since the last retro, never mid-round.
---

# retro

`docs/contributing/fixing-guide.md`'s rule (§2, "a drift you notice is
a line") produces a steady trickle of one-line bookkeeping findings
(`UX-998`). Left alone, the same class of finding recurs indefinitely;
this is the step that turns a repeated class into a proposal to remove
it, rather than reading it again next week.

## Run it

```bash
python3 tools/dev_retro.py
python3 tools/dev_retro.py --since 2026-09-01
```

Reads only what was **added** since the window started - the
bookkeeping ledger, `docs/audits/agent-runs.md`'s friction cell, and
the `Class:`/`Guard:` fields of every task file that closed in the
window - and prints classes by count, the unclassed share, and
bookkeeping lines per ISO week: the one metric this is judged on,
which should fall. `--since` defaults to the newest
`docs/audits/retro-*.md` date, so a week nobody ran it is not silently
absorbed into the next window.

## Add what the tool cannot read

If `gh` answers, add the failed run count for the window it did not
already have a bookkeeping line for:

```bash
gh run list --branch main --status failure --limit 20
```

A run already filed as a bookkeeping line or a run ledger row is not
counted twice - it is the same finding the tool already read.

## Write the report and open the PR

Write `docs/audits/retro-<date>.md`: the class-count table `dev_retro.py`
printed, the command that produced it, and up to three proposals for
the top classes, each marked `optimization` (`UX-994`'s cap does not
apply to them). Then:

```bash
git add docs/audits/retro-<date>.md
git commit -m "retro: <date>"
gh pr create --title "retro: <date>" --body "the table and the command"
```

**It proposes; it does not build.** Implementing a proposal is a
row of its own, worked the normal way - the `retro` skill's job ends
at the PR, the same boundary `UX-999`'s Out of Scope draws.

## What this is not

Not a task filer: an unattended id would race a live session's own
filing. Not a second keyword sweep: eight hand-picked themes left 276
of 350 friction rows unclassed, which is why the class key is a
command token read off the text rather than a guessed theme. See
`docs/contributing/fixing-guide.md` for the process rules this
automates the bookkeeping of.
