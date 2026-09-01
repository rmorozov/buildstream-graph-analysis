---
name: decompose
description: Turn a filing, or a round of filings, into a work order before any code is written - the surfaces each item touches, the input classes its guards must cover, which items can run in parallel, and which share one gate. Use before implementing any UX-* item wider than one module, and use when planning a round of several items.
---

# decompose

A task file says *what* and *why*. This says how it splits: into
surfaces, into input classes, into tracks. Fifteen lines, derived by
the commands below, pasted under a `## Decomposition` heading in the
task file (one item) or the round document (a batch). The rule it
serves is [fixing guide](../../../docs/contributing/fixing-guide.md) §2
(stay inside scope) and §3 (every claim measured); this is the step that finds the scope before it is crossed.

## 1. Surfaces — what the change will touch, derived

```bash
git diff --stat                               # after a five-minute sketch of the change
make test-touching ARGS=--why                 # which guards name those modules
python3 tools/dev_js_deps.py --graph bga/viewer   # only for a viewer change
bga analyze --schema | head -40               # only when a published key moves
```

Write one row per surface: `module | contract (key added / renamed) |
document it makes wrong (§3.10) | guard family that reads it`. A
renamed key is a version bump (§3.7); a document row with no fix in
this item is a `§3.11` filing, decided now rather than found at commit.

## 2. Partition — the input classes the guards must cover

This is test analysis, not test writing: name the classes first, then
one guard per class, then the boundary between classes. The dimensions
this repository's defects have actually fallen on:

| dimension | classes | boundary that bit |
|---|---|---|
| population | 0 · 1 · many (the capacity sweep's size) | `UX-388` (0), `UX-365` (1), `UX-367` (many) |
| contract version | legacy, read-only · current | `UX-384` |
| capture mode | cold · incremental | `UX-431` — several defects appear only warm |
| Plane 2 | absent · hook only · spine on | `UX-406` — every process twice with the spine |
| reader | DOM shim · real Chrome · the export | `UX-359` — the shim measured a page 14 % shorter |
| host | this machine · CI only (verify §7) | `UX-418` — no local instrument exists |

A class with no guard is written down as a gap and filed, not left as
a comment. A guard that covers two classes at once has not covered
either (falsify skill: one mutation, one claim).

## 3. Tracks — what can run in parallel

Two items are one track when their surface rows overlap; otherwise
they are parallel. Three files are shared by *every* item and are the
merge hotspots, so a track never touches them — the orchestrating
session does, once, at the end:

```text
docs/backlog/scenarios/README.md    the index counts and the row
docs/backlog/scenarios/closed.md    the closed row
tests/tiers.py, tests/ci_reference.json   a new file's tier and CI seconds
```

A parallel track runs in its own worktree (the Agent tool's worktree
isolation, or `git worktree add`), commits on its own branch, and
reports the surfaces it actually touched against the ones it declared.
The `verifier` agent reads each track before it merges.

## 4. The gate — what runs once for the batch

Per item, the inner loop: `make test-touching`, then every new guard
mutated red (falsify skill). Per batch: one PR opened *first* (verify
§7 — a branch with no PR collects no CI), one merge, one `make test`
here. Fixing guide §3 still asks for the suite before any single item
is marked done; `UX-500` is the measurement that decides whether the
batch gate may replace it. Until then the batch gate is *in addition*.

## What goes in the file

```text
## Decomposition
surfaces: bga/correlate.py (key added, no bump) · bga/viewer/structured.js · docs/guides/cli.md (§3.10)
guards:   test_the_join_is_a_view.py (population 0/1/many) · test_the_report_you_can_attach.py (many)
gap:      spine-on class has no guard — filed UX-NNN
track:    parallel with UX-MMM (disjoint surfaces); serial after UX-KKK (both touch structured.js)
gate:     batch PR #NNN
```

Five lines, every one derived above. Longer means the split has not
been found yet.
