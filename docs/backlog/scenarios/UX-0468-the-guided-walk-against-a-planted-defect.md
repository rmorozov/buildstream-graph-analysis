# UX-468: no walk of the guides has ever started from a defect somebody planted

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-465` stages 1–2 and 4 (a project whose defect is a parameter) · reads `UX-467`'s answer key | **Found by:** round 72, thread 3 of the audit — whether the README and guides flow really lets you spot a real build efficiency problem | **Serves:** the reader who follows the front door end to end and arrives somewhere other than the problem | **Topic:** docs

## Motivation

Rounds 58, 60 and 69 each walked `bga snapshot → bga view → Perfetto`
and filed what they found. Every one of those walks started from a
project and asked what the tool said about it. None started from a
**defect chosen in advance** and asked whether the flow leads to it.

Those are different questions. A walk that starts from the output
grades the output's plausibility; only a walk with a planted answer can
report a miss. And a miss is the failure mode the guides actually have
— `UX-246` found the journey guide never reached what-if, and
`UX-281` found the satellite pages were dead ends, both of which a
plausibility walk had passed over.

`UX-465` stage 4 makes the defect a parameter of the generated
project, which is what turns this from an anecdote into a repeatable
measurement.

## Required Fix

For each of three planted defects — one per reader whose coverage
`UX-463` measured as thin (local-optimizer, recipe-author,
graph-owner):

1. Generate the project with the defect, capture it, and record the
   **exact click and command path** from `README.md` to the sentence
   that names the defect: every document opened, every command run,
   every page section visited, and the count.
2. Record where the path breaks: a guide that does not link onward, a
   page that shows the number without the sentence, a Perfetto query
   that needs an element name the page never offered.
3. One row per break, filed before the walk's own commit lands
   (fixing guide §3.11).

The deliverable is the recorded walk, in `docs/audits/`, with the
counts — not a list of impressions.

## Out of Scope

- Fixing the breaks. They get rows; a walk that both finds and fixes
  is a walk whose findings nobody can check.
- Rewriting the guides wholesale. `UX-231`'s rule — every direction
  names its reader — already governs their shape.
- Readers whose coverage is already complete. The capacity-operator's
  two findings are both produced by a committed capture, and a fourth
  walk for it is spend without a gap behind it.

## Acceptance Test

A document under `docs/audits/` naming, per defect, the number of
documents opened and commands run before the tool named the defect,
and the breaks found — with each break carrying its filed row id.

## Outcome

**Round 72 · 2026-09-01 · Status: 🟢 Done — the walk is in `docs/audits/planted-defect-walk-round-72.md`, and one of the three readers never reaches the answer**

### What was built and run

Three specs, committed, one per thin-coverage reader, generated with
`tools/bga_gen_project.py` (`UX-465` stage 4 — the defect is a
parameter) and built by a real `bst` 2.7.0 under `bga snapshot`:

```console
$ python3 tools/bga_gen_project.py --spec tests/fixtures/specs/planted-serial-chain.json --out /tmp/chain
{"out": "/tmp/chain", "name": "planted-serial-chain", "elements": 7}
$ cd /tmp/chain && bga snapshot -- bst build all.bst
```

| walk | reader | plant | answer key |
|---|---|---|---|
| 1 | local-optimizer | `mod3.bst` 8.0s among five 0.3s siblings | `mod3.bst` |
| 2 | recipe-author | `base.bst` gates six apps, stages 20,000 files | `base.bst` **and its reach** |
| 3 | graph-owner | six 1.5s elements in one strict chain | the shape |

### The counts, which is what the row asked for

| walk | documents opened | commands run | key reached? |
|---|---|---|---|
| 1 | 1 (`README.md`) | 1 (`bga snapshot`) | yes — first line of `Next:` |
| 2 | 1 | 2 (`+ bga blast`) | element yes; reach only behind command 2, and never via the reader |
| 3 | 1 | 1 | **no** |

### Walk 3, pasted, because it is the finding

```text
"diagnosis": "scheduler_bound", "chain_share": 0.865, "chain_bound_share": 0.9
"This build is scheduler-bound, not chain-bound: the critical path is 87% of
 wall-clock, below the 90% chain-bound line, so the time is going somewhere
 other than the chain."

readers: ['local-optimizer', 'recipe-author', 'ci-gatekeeper', 'capacity-operator']

Next:  ... This build is scheduler-bound: 1.4s of wall-clock is beyond the
       critical path - the sweep says what more builders would buy.
Parallelism Profile: min=1.0x, avg=1.1x, max=2.0x
```

On a graph that is a line. The falsifier, same spec with `seconds`
1.5 → 4.5 and the graph byte-identical:

```text
  per link   chain_share   diagnosis          graph-owner offered?
    1.5s        0.865      scheduler_bound    no
    4.5s        0.950      chain_bound        yes
```

The diagnosis follows build length, not shape, because `chain_share`'s
denominator is wall-clock and wall-clock carries the ~1.3s BuildStream
head the same report identifies as *"not a scheduling issue"*.

### The rows, filed before this commit (§3.11)

| break | row |
|---|---|
| `chain_share`'s denominator carries a constant, so one graph gets two verdicts | `UX-477` 🔴 |
| the graph-owner reader is dropped on a strict chain | `UX-478` 🔴 |
| a chain-bound build publishes no blast radius, so the recipe-author is led to `latent-heavies` | `UX-479` 🔴 |
| `mesh-graph` calls the chain a mesh | `UX-475`, already open — this walk adds a by-construction reproducer |
| `blast-radius-ranking` ranks six elements tied at one downstream | `UX-474`, already open — the tied variant |

### An instrument of my own that did not discriminate

The first check of whether the answer reached the **page** was
`answer_key in exported_html`. It returned `True` for all three walks
— including walk 3, where the reader is absent — and `True` for
`"graph-owner"` in all three, because the page ships the reader
vocabulary and every element name as data regardless. A text scan that
cannot tell a rendered conclusion from a payload string: fixing guide
§5, in this walk's own method. It was replaced by the `readers` block
of `analyze --format json`, which is the producer's decision rather
than a substring. Recorded rather than quietly fixed, per the `verify`
skill.

### Deviation from the Required Fix

The Required Fix asked for the click path through the **page** as well
as the command path. What is recorded is the command path plus the
published `readers` index, for the reason above: the only page-side
instrument this walk could build without a browser harness was the
substring scan, and it did not discriminate. The reader index is what
the page routes by (`UX-372`), so it answers the same question one
level up. Named as a deviation rather than presented as the whole
thing.

### Verification

```text
make lint                  clean (ruff + PyMarkdown)
dev_close_task.py --check  0 problem(s) over 3 properties, 477 backlog rows
make test                  5560 passed, 28 skipped, 1 warning in 316.56s (0:05:16)
```

The first `make test` of this item was **red**, and the guard was
right: `UX-478`'s `criticality` Out of Scope bullet stated its reason
after a `.**` with no space, so
`test_every_out_of_scope_entry_names_a_task_or_states_a_decline` could
not see the clause it requires. Rephrased onto the em-dash form, and
the entry says more than it did before.
