# UX-714: the orchestrator's share is a bare figure that has moved

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-707 (the rebuild count), UX-711 (the reader that works on a live session), UX-511 (dated or derived) | **Found by:** architecture review 17, checklist item 3 | **Serves:** the session pricing a batch against a figure it believes | **Topic:** docs | **Area:** tools | **Shape:** judgement

## Motivation

`CLAUDE.md` steers every session with:

> its cost is the live context at each rebuild, **73 % of its tokens
> when measured**

No window, no date, no command. The `decompose` skill carries the
source with a window — *"from round 46 on: 11 rebuilds were 3.76M of
5.16M tokens (73 %)"* — so the skill is a record and `CLAUDE.md`'s copy
is a bare figure, `UX-549`'s shape exactly.

Measured today on the same session, with the reader `UX-711` fixed:

```console
$ python3 tools/dev_track_cost.py --session <this session>.jsonl
rebuilds 136  tokens 63,966,732  share 46.9%
```

**46.9 %, not 73 %** — 26 points, over 136 rebuilds rather than 11.

The two are not a controlled pair: 73 % was a window from round 46, this
is the session entire, and a share falls when the denominator grows. So
the finding is not "73 % is wrong". It is that a reader cannot tell
which of those two things the sentence means, because the sentence
carries neither the window nor the date that would say.

## Required Fix

`UX-511`'s rule: dated or derived. The figure carries the window and
the date it was taken on, in both documents, or `CLAUDE.md` drops the
number and points at `decompose`, which has room for the record. Which
of the two is a judgement about what a one-page steering document is
for, and this row proposes the second — the page budget is already
tight enough that `UX-711` had to rewrap a paragraph to fit.

## Out of Scope

- Re-measuring on a controlled window. Worth doing and it is `UX-707`'s
  ledger that would do it, not this row; this is about the sentence.
- The 73 % figure's correctness at the time. It was measured and
  recorded; nothing here disputes it.

## Acceptance Test

No steering document carries a bare share. Mutation: put a bare
percentage back into `CLAUDE.md` — a clause reddens, or the figure is
absent and the sentence points at the record.

## Outcome

**The gap, measured.**

```console
$ grep -n "%" CLAUDE.md
31:context at each rebuild, 73 % of its tokens when measured; a result over a screen goes to the scratchpad (`UX-711`). `measure`, `falsify`, `verify`
37:  that produced it. "roughly 5% noise" is not a number; this repository
```

Line 31's `73 %` carried neither a window nor a date. The `decompose`
skill's own record (§5) had the window — *"from round 46 on"* — but no
date either.

**The close, measured.**

```console
$ grep -n "%" CLAUDE.md
37:  that produced it. "roughly 5% noise" is not a number; this repository
```

No bare share remains; line 31 now reads *"its cost is the live
context at each rebuild — the `decompose` skill carries the measured
share, with its window"*. `decompose`'s §5 now reads *"Measured on
this session from round 46 on, at round 94 (2026-09-05): 11 rebuilds
were 3.76M of 5.16M tokens (73 %)"* — round 94 and its date are `UX-
707`'s own Outcome, which took this same measurement.

**Mutations.**

| mutation | reddened | count |
|---|---|---|
| put `73 % of its tokens when measured` back into `CLAUDE.md`'s line 31 | `test_no_line_carries_a_bare_share` | 1 failed, 130 passed |

First attempt scoped the guard to the whole physical line, and it did
**not** discriminate: line 31 also carries `` `UX-711` `` two clauses
after the share, which pinned the line by accident and left the
mutation green. Rescoped to the comma/semicolon/em-dash-delimited
clause; the same mutation then reddened as above. Reverted from a
scratch copy, confirmed green.

**Deviation.** None from the Required Fix. `CLAUDE.md`'s page-budget
guard (`test_it_stays_about_a_page`) stayed at 80 lines throughout,
checked after every edit in this and the paired `UX-713` commit.
