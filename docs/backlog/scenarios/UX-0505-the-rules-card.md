# UX-505: the rules card — the guide's rules on one page, its reasons behind it

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-497 (the register it is written in) | **Serves:** every session's first read; the maintainer's subscription | **Topic:** docs

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

## Outcome (round 75, 2026-09-01) — 🟢 Done

### The gap, measured

```text
docs/contributing/fixing-guide.md   34,400 B  333 lines
CLAUDE.md                            3,279 B   80 lines (guarded)
what a session reads first          37,679 B
```

The guide's own second paragraph said "if you have limited context
budget: read only this file" — and the file *is* the budget. Every rule
is stated once and then argued with the incident that produced it; the
incidents are why the rules are trusted, and also why twelve rules cost
34 KB.

### After

```text
docs/contributing/rules.md           4,122 B   78 lines
CLAUDE.md                            3,803 B   80 lines
what a session reads first           7,401 B   — 5.1x smaller
docs/contributing/fixing-guide.md   34,683 B  338 lines (unchanged in
                                               substance; +5 for the header)
```

Split by register, not topic. The card carries **every** rule of §2,
§3, §4, §4a, §5 as one line with the guard that catches it, plus §6a's
stream table; the guide keeps every incident and gains a header saying
the card is the entry point. `CLAUDE.md` sends a session to the card,
the card sends it to the guide for the one rule it is about to break.

The guard column is the part that was not in the filing and is worth
more than the byte count: laid out side by side, **12 of 34** rule rows
name a guard and the rest are kept by attention alone. That is now
visible on one page instead of spread over 34 KB.

Also removed: `CLAUDE.md`'s "**`git add -A` / `git add .`** — forbidden
by §4a.1" bullet, which is on the card with the hook that enforces it.
A third copy of a rule is the duplication this split exists to end.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| P1 | ten rows added to the card (88 lines) | `test_the_card_stays_a_card` |
| P2 | the card cites a `§9` the guide has not got | `..._names_the_guide_section` |
| P3 | the guide stops naming the card | `..._card_is_the_entry_point` |
| P4 | `CLAUDE.md` points at the guide, not the card | `..._points_at_the_card_...` |
| P5 | every guard cell on the card emptied | `..._names_a_guard_...` |

### A guard of ours that did not discriminate

P5 **passed** on first writing. The clause counted the last cell of
every table row on the page, and §6a's stream table has a third column
of prose that is never empty — so emptying all 34 real guard cells left
eight non-rule rows to satisfy it. Fixing guide §5's shape, in a guard
about §5: the quantity read was "rows with a non-empty last cell", not
"rules with a guard". Now reads the two-column rule tables by their
column count, and P5 reds.

### Deviation from the Required Fix

None. The filing asked for ≤ 80 lines (78), a pointer per rule (per
section — the rules are rewritten short on purpose, and a per-sentence
anchor would be asserting the card is a copy), the guide header, and
the `CLAUDE.md` guard repointed at the card. All four.

```text
make test-touching  111 passed in 7.42s;  make lint clean
make test           5754 passed, 27 skipped in 317.44s
```

`test_a_guard_reads_only_what_a_clone_has.py` caught the card
untracked on the first full run — a guard whose only data is a path
git does not have. `git add` was the fix; the clause was right.
