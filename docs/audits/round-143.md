# Round 143 — every agent names its model and effort

Run on 2026-09-27 off main at `d7e74b1c` (`#295`, round 142), from Ruslan's
ask to review the agent workflow's models and efforts for cost against
value, and whether recent rounds call for new roles. He took the
targeted variant the same morning.

```text
closed   UX-1039
filed    UX-1040 (the paired implementer reading) UX-1041 (the install and sweep hook)
index    dev_close_task.py --counts: 1002 scenarios, 17 open, 985 closed
```

## The rework sat between tracks

Round 142's tracks each passed against their base; merged, 13 guards
went red, and the opus runs after the merge cost 1.31M fresh tokens
beside the implementers' 3.94M on sonnet. Four runtime gaps passed every
verifier and reached Ruslan's review. A stronger model per track sees
neither, so the round gives the seams owners: `integrator` (merge, the
shared budgets after each merge), `walker` (the merged page), `closer`
(§7a steps 1-6, on sonnet).

## Size predicts a track's rework

Over 180 verified sonnet tracks, rows over 150 lines of code were held
53% and re-run 23%, against 31% and 2% at 20 lines or fewer; the shape
label barely separates them (mechanical 34%, bounded 32%). So opus goes
to architect-shaped judgement rows and rows over 150 lines, and
`UX-1040` reads opus at `low` against sonnet at `medium` on four pairs
before anything else moves.

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| researcher | sonnet | escapes across 999 task files, by class and catcher | 120k | 40 | 4.9 m | escape language is unstandardised; three keyword passes before reads separated escapes from noise |
