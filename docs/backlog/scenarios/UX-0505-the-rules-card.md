# UX-505: the rules card — the guide's rules on one page, its reasons behind it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-497 (the register it is written in) | **Serves:** every session's first read; the maintainer's subscription | **Topic:** docs

## Motivation

The fixing guide is "read this first, every session" and it is 34,113
bytes. Its first paragraph says "if you have limited context budget:
read only this file" — and the file is the budget. Measured in round
74:

```text
docs/contributing/fixing-guide.md     34,113 B   331 lines
  §3 item 6 alone (the annotation rule)         1,214 B, one paragraph
  §5 hard rule on proxies                         1,376 B, one bullet
CLAUDE.md                              3,279 B   (guarded ≤ 80 lines)
```

Each rule is stated once and then argued with the incident that
produced it. The incidents are the reason the rules are trusted, and
they are also why a session pays 34 KB to learn twelve rules.

## Required Fix

Split by register, not by topic:

- **The card** — `docs/contributing/rules.md`, ≤ 80 lines: every rule
  in §2-§5 as one line each with its guard's file name, the §6a
  stream table, and a pointer per rule to the guide's paragraph.
  `CLAUDE.md` sends a session to the card; the card sends it to the
  guide only for the rule it is about to break.
- **The guide** keeps every incident and argument, unchanged in
  substance, and gains a one-line header saying the card is the
  entry point.
- Guard: every rule sentence on the card has a matching heading or
  anchor in the guide (so the card cannot carry a rule the guide does
  not argue), and the card stays ≤ 80 lines. The existing
  `test_claude_md_points_at_the_guide_rather_than_restating_it`
  becomes "points at the card".

## Out of Scope

- Rewriting any rule — the split moves sentences; a rule that reads
  wrong once isolated is a separate filing.
- The skills — already the on-demand layer; they point at the guide
  and that stays true.

## Acceptance Test

`wc -c` of what a session reads first drops from 34 KB to the card's
size, pasted; the card guard red when a rule is added to the card
without a guide anchor, and when the card passes 80 lines.
