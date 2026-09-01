# The guided walk, from a defect somebody planted (`UX-468`)

Rounds 58, 60 and 69 each walked `bga snapshot → bga view → Perfetto`
and asked what the tool said. This walk asks the other question: three
defects were **chosen first**, generated into real BuildStream projects
with `tools/bga_gen_project.py` (`UX-465`), built by a real `bst`, and
the walk records how far the front door gets a reader towards the
answer that was planted.

BuildStream 2.7.0, `bwrap` 0.11.0, busybox applets, 4 cores. Every
number below is a paste from a run of the command shown.

## The three plants

| walk | reader | spec | the defect, and the answer key |
|---|---|---|---|
| 1 | local-optimizer | [`planted-one-heavy-element`](../../tests/fixtures/specs/planted-one-heavy-element.json) | six independent modules under one toolchain; `mod3.bst` costs 8.0s and the other five 0.3s. **Key: `mod3.bst`.** |
| 2 | recipe-author | [`planted-fat-shared-base`](../../tests/fixtures/specs/planted-fat-shared-base.json) | `base.bst` is a build dependency of six apps and stages 20,000 files. **Key: `base.bst`, *and its reach* — changing it rebuilds six.** |
| 3 | graph-owner | [`planted-serial-chain`](../../tests/fixtures/specs/planted-serial-chain.json) | six 1.5s elements in one strict chain. **Key: the shape — no number of builders shortens this.** |

Reproducing one:

```bash
python3 tools/bga_gen_project.py \
    --spec tests/fixtures/specs/planted-serial-chain.json --out /tmp/chain
cd /tmp/chain && bga snapshot -- bst build all.bst
```

## Walk 1 — local-optimizer: the key is named on command 1

One document (`README.md`), one command. `bga snapshot` printed:

```text
Next:
  mod3.bst is the longest thing on the critical path at 7.2s, 100% of it - the build cannot finish sooner than this chain.
    bga blast mod3.bst .../run
  mod3.bst is the first thing to fix - this is what changing it rebuilds.
```

**Documents opened: 1. Commands run: 1. The key is in the first
screen.** That is the whole `UX-218`/`UX-365` design working.

What the *findings* said is a different story. `time-concentration` —
the finding whose title is literally "Where the time is" — did not
fire, on a build where one element is 100% of the critical path. The
reader that was offered leads with `blast-radius-ranking`:

```text
Elements Most Worth Optimizing First (by blast radius):
    1. mod3.bst (1 downstream elements)
    2. mod0.bst (1 downstream elements)
    3. mod1.bst (1 downstream elements)
```

Six elements tied at one downstream each, ranked. `mod3.bst` leads on
the tiebreak, not on the quantity the heading names — the same defect
`UX-474` filed against a list of zeros, in its tied variant. The walk
reached the key **despite** the ranking, through the `Next:` block.

## Walk 2 — recipe-author: the element is named, the reach is not

```text
Next:
  base.bst is the longest thing on the critical path at 21.0s, 95% of it - the build cannot finish sooner than this chain.
  base.bst is the first thing to fix, worth 21.0s - this is what changing it rebuilds.
    bga blast base.bst .../run
```

**Documents: 1. Commands: 1** for the element; the *reach* — how many
elements a change to `base.bst` rebuilds — is behind a second command
(`bga blast`), which the block does offer. Call it 1 document, 2
commands.

But the reader this walk is about is not routed there. The recipe-author
is offered exactly one finding:

```text
"id": "recipe-author", "leads_with": "latent-heavies",
"findings": ["latent-heavies"]

Waiting off the critical path, worth nothing to fix today: app1.bst (1s), app2.bst (1s) (+1 more)
```

The person who owns `base.bst` — 21.0s of a 22.0s critical path, gating
six elements — opens their reader and is told about three apps that are
worth nothing to fix. **No blast-radius finding of any kind fired on
this run**, so the reach is published nowhere:

```text
$ bga analyze @last --diagnostics --format json | jq -r '.findings[].id'
wait-category  time-concentration  mesh-graph  joint-saving  latent-heavies
cache-hit-ratio  confidence  memory-envelope  capacity-recommendation
criticality  certified-headroom  efficiency-score
```

The mechanism is a branch, and it is doubly closed
(`bga/findings.py:1329` and `:1111`):

```python
    if chain_bound and heaviest_on_path(result):
        ...                                    # the chain-bound arm
    else:
        findings.extend(_ranking_findings(result, chain_bound))

def _ranking_findings(result, chain_bound):
    if chain_bound or not top_blast_radius:
        return []
```

So a **chain-bound** build publishes no blast radius for an actionable
element — and a project whose defect is one fat shared base is exactly
the shape that is chain-bound. `UX-474` recorded the inner guard as
unreachable while working `UX-467`; this walk is what it costs. The
only blast finding that survives is `blast-radius-structural`, which
selects on `is_structural_kind` (`UX-76`/`UX-258`, and rightly so), so
it named the generator's scaffolding on the other two walks:

```text
Reaching most of the graph by design: toolchain.bst (7 downstream), runtime.bst (7 downstream)
  - structural elements (import) whose dependents are the graph's shape, not a task
```

and could never name a `manual` element — **UX-479**.

`mesh-graph` also fired here, on a star: *"80% of elements have zero
slack — this graph is a mesh of near-equal chains"*. `UX-475` on a
second shape.

## Walk 3 — graph-owner: the reader is not offered at all

The graph is six elements in one line. The tool said:

```text
"diagnosis": "scheduler_bound", "chain_share": 0.865, "chain_bound_share": 0.9,
"sentence": "This build is scheduler-bound, not chain-bound: the critical path is
             87% of wall-clock, below the 90% chain-bound line, so the time is
             going somewhere other than the chain."

Next:
  link3.bst is the longest thing on the critical path at 2.0s, 23% of it
  link0.bst is the first thing to fix
  This build is scheduler-bound: 1.4s of wall-clock is beyond the critical path
      - the sweep says what more builders would buy.
```

`Parallelism Profile: min=1.0x, avg=1.1x, max=2.0x`. More builders buy
nothing on a strict chain, and the front door offers the sweep anyway.

The published reader index for this run:

```text
['local-optimizer', 'recipe-author', 'ci-gatekeeper', 'capacity-operator']
```

**No `graph-owner`.** Both of R3's findings (`mesh-graph`,
`criticality`) are absent, so `reader_index`'s dead-control rule
(`UX-194`) drops the reader — on the one project whose entire defect is
the graph. **Documents: 1. Commands: 1. The key was never reached, by
any path the front door offers** — UX-478.

### Why, measured: the diagnosis is a function of build length

`chain_share` is critical path over **wall-clock**, and wall-clock
carries a fixed BuildStream head the graph cannot explain — the run's
own `wait-category` names it: *"12.1% of wall-clock time is UNTRACKED
HEAD (1.25s) — real time before the tracked-task window started
(BuildStream startup, cache query, sandbox staging)"*.

So the same spec with only the per-element seconds changed, 1.5 → 4.5,
shape byte-identical:

```text
  per link   critical path   chain_share   diagnosis          graph-owner offered?
    1.5s        8.95s          0.865       scheduler_bound    no
    4.5s       26.9s           0.950       chain_bound        yes
```

```text
1.5s: "This build is scheduler-bound, not chain-bound: the critical path is 87%
       of wall-clock, below the 90% chain-bound line"
4.5s: "This build is chain-bound, not scheduler-bound: the critical path is 95%
       of wall-clock, at or above the 90% chain-bound line"
```

One graph, two verdicts, decided by how long the elements sleep.
`UX-456` measured the same threshold straddling on `examples/06` across
twenty cold builds (0.853–0.916, 19 of 20 below the line) and read it
as noise near a cut. It is not noise: the denominator includes a
constant, so **short builds are systematically diagnosed
scheduler-bound whatever their shape** — UX-477.

And at 4.5s, where R3 *is* offered, it leads with:

```text
Note: 100% of elements have zero slack - this graph is a mesh of near-equal
chains, so savings on one element are often capped by the next chain rather
than by its own duration
```

There is no next chain. `UX-475`, now with a reproducer that is a chain
by construction rather than by inspection.

## The count

| walk | documents | commands | key reached? | where |
|---|---|---|---|---|
| 1 local-optimizer | 1 | 1 | yes | `Next:` block, first line |
| 2 recipe-author | 1 | 2 | element yes, reach behind `bga blast` | `Next:` block; **not** via the reader |
| 3 graph-owner | 1 | 1 | **no** | reader absent; the sweep offered instead |

## Breaks, and their rows

| # | break | row |
|---|---|---|
| B1 | `chain_share`'s denominator includes the untracked head, so the diagnosis follows build length, not shape — one graph, two verdicts | [UX-477](../backlog/scenarios/UX-0477-the-chain-share-denominator-carries-a-constant.md) |
| B2 | the graph-owner reader is dropped on a strict chain, because both R3 findings key off the diagnosis B1 got wrong | [UX-478](../backlog/scenarios/UX-0478-the-graph-owner-vanishes-on-a-graph-problem.md) |
| B3 | a chain-bound build publishes no blast radius for an actionable element, so the recipe-author who owns the shared base is offered `latent-heavies` and nothing about reach | [UX-479](../backlog/scenarios/UX-0479-a-chain-bound-build-publishes-no-blast-radius.md) |
| B4 | `mesh-graph` calls a strict linear chain a mesh | `UX-475`, already open — this walk adds the by-construction reproducer |
| B5 | `blast-radius-ranking` ranks six elements tied at one downstream | `UX-474`, already open — the tied variant of its list of zeros |

Per `UX-468`'s Out of Scope, none of them is fixed here.

## One instrument of this walk that did not discriminate

The first check of whether the answer reached the **page** was
`answer_key in exported_html`. It returned `True` for all three walks
including walk 3, and for `"graph-owner"` in all three — because the
page ships the reader vocabulary and every element name as data
whether or not the reader is offered. A text scan that cannot tell a
rendered conclusion from a payload string, which is fixing guide §5
in this document's own method. The evidence used above is the
`readers` block of `analyze --format json`, which is the producer's
own decision rather than a search for a substring.
