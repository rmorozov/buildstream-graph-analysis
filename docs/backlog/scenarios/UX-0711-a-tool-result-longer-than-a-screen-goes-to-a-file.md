# UX-711: a tool result longer than a screen goes to a file

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-707 (the rebuild count) | **Serves:** the orchestrating session, whose live context is what every rebuild re-buys | **Topic:** docs | **Shape:** judgement

## Motivation

Round 94 attributed this session's tokens to the tools whose results
entered them: one job-log read was 26k over five calls, one
workflow-jobs listing 36k over three, one persisted read 35 KB in a
single result. Each stays in the live context and is re-entered at
every rebuild (`UX-707`); the `orient` skill says "lines not files"
for source and says nothing about tool output.

## Required Fix

One rule in the `orient` skill and one line in `CLAUDE.md`'s pipeline
paragraph: a result over a screen (60 lines) is written to the
scratchpad and read by `head`, `grep` or the tool's own `tail_lines`;
a log is never taken whole. A guard reads the two documents for the
rule's sentence; the number that shows it worked is `UX-707`'s live
context at rebuild, before and after one round.

## Out of Scope

- Changing what the tools return — a wrapper for every tool is a
  second harness; the rule is the session's discipline.

## Acceptance Test

The sentence in both documents (guarded); one round's `UX-707`
figure pasted beside round 94's; mutation: the sentence removed from
`orient` — the guard reddens.

## Outcome

🟢 Done. The rule is in both documents and guarded; the figure is
recorded as a baseline rather than claimed as a win.

`orient` gains a fourth rule (its count moved with it) and `CLAUDE.md`'s
pipeline paragraph a sentence: a result over **60 lines** goes to the
scratchpad and comes back through `head`, `grep` or the tool's own
`tail_lines`. Three clauses in
`test_the_agent_configuration_holds.py` read the two documents for the
rule's load-bearing words and for the routes that make it obeyable — a
budget with no way to keep it is not a rule.

### The instrument could not read a live session

`--session` is how `UX-707`'s figure is taken, and it raised
`JSONDecodeError` on this session:

```console
$ python3 tools/dev_track_cost.py --session <this session>.jsonl
json.decoder.JSONDecodeError: Expecting ',' delimiter: line 1 column 605
```

A session measuring **itself** reads a transcript still being appended
to, so the last line is half written — and every one of the tool's four
readers called `json.loads` bare. They now go through one `_record()`
that returns `None` on a partial line. Without this the row's own
acceptance test is unobtainable from inside the run it describes, which
is why the fix is here rather than filed.

### The figure

```console
$ python3 tools/dev_track_cost.py --session <this session>.jsonl
rebuilds 136  tokens 63,966,732  share 46.9%
median rebuild 502,646   max 766,012
```

Round 94's reading was **11 rebuilds, 3.76M of 5.16M tokens (73%)**.

**These are not a controlled pair and the row should not be read as if
they were.** Round 94 measured a window from round 46; this is the
session entire, 136 rebuilds over three weeks, and the share falls
partly because the denominator grew. The two rebuilds during this round
were 81,102 and 91,922 against the 502,646 median — but they *precede*
the rule being written, and a container restart reset the context
between them, so they are not evidence for it either.

What the row can honestly claim: the rule is stated, guarded, and the
instrument that prices it now works from inside a live session. The
next round is the first that can measure it against this baseline.

### Mutations

| mutation | guard |
|---|---|
| the sentence removed from `orient` | the orient clause |
| the sentence removed from `CLAUDE.md` | the CLAUDE.md clause |
| the budget kept, `head`/`grep` dropped | the routes clause |

### Where the page budget bit

`CLAUDE.md` is capped at 80 lines and the addition made it 81 — caught
by its own guard, after this round had already committed and pushed it.
The paragraph is rewrapped to three lines and the rule split by reader:
`CLAUDE.md` carries the rule and the id, `orient` the 60-line budget
and the routes. The guard now reads each document for what that
document is for, rather than the same three words twice.

### Deviation

One addition beyond the Required Fix: the `_record()` tolerance in
`dev_track_cost.py`. It is not scope creep but the row's own
precondition — the Acceptance Test asks for a `UX-707` figure, and
before this the tool could not produce one for a running session.
