# Design round 91: can `bga` answer the utilization question — and whose question it is

Run on 2026-09-05, after round 90 merged. A design round (§6a): the
user asked whether the tool can answer three roles' questions —
the CI owner's "are the cores the binding resource without
overcommitting memory", the element owner's incoming dependencies
and blast radius, the graph owner's evidence that the shape lets a
cold build use the machine and a cached build rebuild cheaply — and
asked to be challenged. One researcher inventoried what the tool
computes today; the argument is Direction 17 in `directions.md`; the
ten filings are `UX-675`..`UX-684`.

## What the tool answers today

```text
builders and per-element max-jobs        known, reconciled (UX-377)                       ANSWERED
cores busy over time                     none — "traced processes running" counts processes  ABSENT
under-utilized intervals                 idle_periods computed (utilisation/__init__.py:403), never published  DEAD CODE
memory over time                         host-samples.jsonl, five tracks (UX-378/437); no CPU field  PARTIAL
memory in the sweep / queue model        Resource has no MEMORY; static envelope apart      ABSENT
remote execution                         "deliberately unfiled" since round 1 (D5)         ABSENT by decision
fan-out, blast, deciles, weighted        deep (findings.py:1256-1391, blast.py:311-320)    ANSWERED
fan-in, dominators                       0 hits; dominators computed, never surfaced       ABSENT
consolidation / batching / serialization points / chain-vs-mesh   present                  ANSWERED
foundation exemption                     by kind (junction/import/filter/compose/stack)    PARTIAL — a toolchain is not exempt
change frequency, co-change              pairwise churn only; UX-92 stage 3 blocked        ABSENT
cold-build verdict and floors            chain-bound / scheduler-bound, four floors, knee  ANSWERED
cached-build verdict                     none                                              ABSENT
```

## The four corrections

Argued in Direction 17: the objective is the utilization *envelope*
as a series and its violations as intervals, not a core count;
per-element `max-jobs` tuning approximates what a jobserver every
sandbox joins would do dynamically, and the tool owns the injection
path to try it; remote execution is two mechanisms the tool can
price without building either; a blast threshold is replaced by
expected rebuild cost from the change history, with the foundation
tier declared rather than discovered.

## Filed

`UX-675` (the host series gains cores — High), `UX-676` (the
envelope and its intervals — High), `UX-677` (the max-jobs advisor —
High), `UX-678` (memory in the sweep — Medium), `UX-679` (a jobserver
every sandbox joins — Medium, a spike), `UX-680` (remote execution
priced — Medium), `UX-681` (fan-in and the dominator — High),
`UX-682` (change frequency and co-change — High), `UX-683` (the
foundation tier declared — Medium), `UX-684` (the cached-build
verdict — High).

## Agents

| agent | model | task | tokens | tool calls | wall | friction |
|---|---|---|---|---|---|---|
| researcher | sonnet | what the tool answers for the three roles | 121k | 86 | 7 m | telling computed from published needs a grep of the consuming layer for the producing layer's names; docstrings claim what nothing reads |

## Standing

A design round produces no code; the one test edit is the direction walk's count, 1-16 → 1-17, which follows the document by construction. Verified in passing: the blast
weighing (count, building, assembling, measured duration) is what
the brief asked for and already there; `UX-92`'s stage-3 block does
not apply to `UX-682`, which needs kept logs rather than ref
variation.
