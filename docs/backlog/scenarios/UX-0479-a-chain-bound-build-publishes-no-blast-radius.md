# UX-479: a chain-bound build publishes no blast radius, so the recipe-author never learns what their element reaches

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 72, `UX-468`'s planted walk 2 | **Serves:** the recipe-author who owns the element every other element waits for, and is shown three elements that are worth nothing to fix | **Topic:** analysis

## Motivation

`UX-468` generated a project whose whole defect is one fat shared base:
`base.bst` is a build dependency of six apps, costs 21.0s of a 22.0s
critical path, and stages 20,000 files. The recipe-author's published
reader on that run:

```text
"id": "recipe-author",
"question": "Is my element a problem, and what does changing it cost?",
"leads_with": "latent-heavies",
"findings": ["latent-heavies"]

Waiting off the critical path, worth nothing to fix today: app1.bst (1s),
app2.bst (1s) (+1 more) - they bound how far shortening the chain can go
```

The reader's own question is *what does changing it cost*, and the
answer offered is about three other elements that cost nothing. **No
blast-radius finding fired at all:**

```console
$ bga analyze @last --diagnostics --format json | jq -r '.findings[].id'
wait-category  time-concentration  mesh-graph  joint-saving  latent-heavies
cache-hit-ratio  confidence  memory-envelope  capacity-recommendation
criticality  certified-headroom  efficiency-score
```

The mechanism is one branch, closed twice
(`bga/findings.py:1329`, `bga/findings.py:1111`):

```python
    if chain_bound and heaviest_on_path(result):
        ...                                     # the chain-bound arm
    else:
        findings.extend(_ranking_findings(result, chain_bound))

def _ranking_findings(result, chain_bound):
    if chain_bound or not top_blast_radius:
        return []
```

`UX-474` recorded the inner guard as **unreachable** — found while
mutating for `UX-467`, because the caller already decided. This walk is
what the outer branch costs: a build that is chain-bound publishes no
blast radius for any actionable element, and *a build gated by one fat
shared base is exactly the shape that is chain-bound.* The reach is
computed (`elements.blast_radius` carries it) and reaches no reader.

The only blast finding that survives the branch is
`blast-radius-structural`, which selects on `is_structural_kind` —
correctly, `UX-76`/`UX-258`: a toolchain has a thousand dependents on
purpose and that is a fact about the graph, not a task. On the walk's
other two projects it therefore named only the generator's scaffolding:

```text
Reaching most of the graph by design: toolchain.bst (7 downstream),
runtime.bst (7 downstream) - structural elements (import) whose
dependents are the graph's shape, not a task
```

So R2's two graph-shaped findings between them cover the `import` that
nobody edits and nothing else.

## Required Fix

- **Publish the reach on a chain-bound build too.** What `UX-258`'s
  rule excludes is *structural kinds from the ranking*; nothing in it
  says a chain-bound build has no elements worth ranking. Either the
  outer branch stops being exclusive, or the chain-bound arm carries
  its own reach sentence. Say which and why in the code, since the
  branch has now been read wrongly twice.
- **Then delete the inner guard**, which `UX-474` already found cannot
  fire — or, if the outer branch stays, keep it and say in the
  docstring that it is a second belt, so the next mutation round is not
  misled again.
- **A guard whose fixture is chain-bound.** `UX-464`'s
  `shared_base_wide` and this row's `planted-fat-shared-base` are both
  that shape. The clause: a chain-bound run over a graph with one
  6-dependent element publishes a finding naming it, for
  `recipe-author`. It reddens today.

## Out of Scope

- **`blast-radius-structural`'s kind filter.** `UX-76` and `UX-258`
  argued it and the argument holds; a `manual` element with six
  dependents is not the same claim as a toolchain with a thousand.
- **`latent-heavies`.** Its sentence is true — those apps really are
  worth nothing to fix today. It is the wrong lead, not a wrong
  finding, and it becomes the right lead once R2 has the other one.
- **`UX-474`'s own subject**, the ranking that publishes a list of
  zeros. That is the *content* of the finding when it does fire; this
  is about the run where it does not fire at all.

## Acceptance Test

```bash
python3 tools/bga_gen_project.py \
    --spec tests/fixtures/specs/planted-fat-shared-base.json --out /tmp/base
cd /tmp/base && bga snapshot -- bst build all.bst >/dev/null
bga analyze @last --diagnostics --format json | python3 -c '
import json,sys
d = json.load(sys.stdin)
r = next(x for x in d["readers"] if x["id"] == "recipe-author")
print(r["leads_with"], r["findings"])'
```

names a finding whose text carries `base.bst` and its downstream count.

## Outcome

_Not started._
