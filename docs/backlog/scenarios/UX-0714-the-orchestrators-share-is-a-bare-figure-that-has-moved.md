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
