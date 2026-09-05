# UX-706: a task's shape is derived from its text, and names the model that runs it

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-663 (the model advisory), UX-498 (the decompose skill) | **Found by:** round 94, pricing the pipeline | **Serves:** the session deciding which of a round's filings a cheaper model may run, without reading them all | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

The advisory of round 90 put reading and checking on `sonnet` and code
on the session's model, and the ledger has never priced an
`implementer` or a `verifier` run, so nothing said which filings a
smaller model may take. Round 94 read 60 closed tasks: 38 % name a
file in the Required Fix, 5 % name a guard and a mutation in the
Acceptance Test, 15 % touch a contract or process surface; the
`decompose` skill's block appears in 0 task files.

## Required Fix

`tools/dev_close_task.py --shape [UX-NNN] [--write]`: three yes/no readings
of the file's own text — the Required Fix names a file, the Acceptance
Test names a guard and a mutation, either names a contract or process
surface — give **mechanical**, **bounded** or **judgement**; `--write`
puts `**Shape:** word` in the header; `--check` holds every open
row's declared word equal to the derived one. The `implementer` is
handed mechanical and bounded and runs on `sonnet`; judgement is the
session's.

## Out of Scope

- Reading the diff to shape a task — the shape is read before the
  code exists, from the filing; `UX-687`'s impact set prices the diff.
- Re-shaping closed tasks — the word steers a run; a closed row has
  none to steer.

## Acceptance Test

`dev_close_task.py --shape` on every open row; `--check` green after
`--write`; mutation: a typed word in one file → `--check` red on that
row; `derived_shape` returning a constant → the guard's shape clauses
red.

## Outcome

**The gap, measured.** 60 closed tasks of rounds 84-90, three greps
per file (the researcher's run, 145k tokens):

```text
Required Fix names a file            23 / 60   38 %
Acceptance Test names guard+mutation  3 / 60    5 %
touches a contract/process surface    9 / 60   15 %
`## Decomposition` block in any file  0 / 705
implementer / verifier rows in the ledger   0
```

**The close, measured.** `--shape` over the open backlog, then
`--write`, then `--check`:

```text
8 bounded · 35 judgement · 0 mechanical        (43 open rows)
0 problem(s) over 8 propert(y/ies), 703 backlog row(s)
```

**Mutations.**

| mutation | guard | result |
|---|---|---|
| `**Shape:** bounded` → `mechanical` in `UX-0702` | `test_a_task_declares_its_shape.py` · `--check` | 1 failed, 11 passed · 1 disagreement |
| `derived_shape()` returns `"bounded"` always | the same file | 7 failed, 5 passed |

**Deviation.** None. Zero mechanical rows today is the finding, not a
fault of the derivation: no open filing names both its guard and its
mutation in the Acceptance Test, so the first mechanical track is a
filing written to be one.
