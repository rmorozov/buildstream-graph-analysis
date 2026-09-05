# UX-537: forty-eight hand-built documents, and the shared shim they were to become

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-264` (the shared shim), `UX-219` and `UX-254` (two defects this shape has already produced), `UX-523` (found it again) | **Serves:** the next round that adds a standard DOM call to the viewer | **Topic:** guards | **Area:** bga/viewer

## Motivation

`UX-264` replaced twenty-five hand-built `document` objects with one
shared shim. There are forty-eight now:

```text
$ grep -rln "globalThis.document = {" tests/unit/*.py | wc -l
48
$ for f in $(grep -rln "globalThis.document = {" tests/unit/*.py); do
    grep -q documentElement "$f" || echo "$f"; done | wc -l
48
```

None models `documentElement`, though `tests/dom_shim.mjs` - the shared
one - has had it since `UX-264`. So a viewer that reads a standard DOM
property the shims do not carry fails in **ten guards at once**, in
`boot()`'s catch-all, with a message about the harness rather than the
page. That is the third time this exact shape has cost a round:

| | what the model was missing | how it surfaced |
|---|---|---|
| `UX-219` | `createTextNode` | the exported page threw inside `boot()` and rendered the banner |
| `UX-254` | `querySelector` | twelve order guards reported "Could not load this run" |
| `UX-523` | `documentElement` | ten setup errors; the page now guards the write |

Each was fixed by *widening the model rather than avoiding the method*,
and each fix landed in one file. The other forty-seven kept the trap.

## Required Fix

- Count what the forty-eight shims actually differ in, measured rather
  than assumed: which of them need their own `getElementById` policy
  (the reason `installDocument` takes overrides), and which are copies.
- Move the copies onto `installDocument`, one commit, no behaviour
  change - the diff is deletions plus an import.
- A guard that a new hand-built `globalThis.document = {` in
  `tests/unit/` fails, naming `installDocument` and the three defects
  above. That is the part that makes this the last time.
- Then drop `boot()`'s `documentElement?.dataset` guard, whose one line
  of why points here.

## Out of Scope

- The shim's fidelity as a DOM. It is a model on purpose; this is about
  there being **one** of it.
- The browser-tier guards, declined: they drive a real Chromium and
  have no shim to consolidate.

## Acceptance Test

`grep -c "globalThis.document = {" tests/unit/*.py` before and after,
both pasted, and the whole suite green. Mutation: add a fresh
hand-built document to one guard file - the new guard must redden and
name `installDocument`.

## Outcome

**Round 80, 2026-09-02.** Forty-eight when filed; round 80 landed two
more first. **The census, before** - 54 literals in 50 files, none with
`documentElement`:

```text
$ grep -rln "globalThis.document = {" tests/unit/*.py | wc -l
50
$ ... | while read f; do grep -q documentElement "$f" || echo "$f"; done | wc -l
48
```

**What they actually differ in** — brace-matched out of the Python and
bucketed by key, which is the measurement this row asked for before
converting anything:

```text
key              literals carrying it    distinct bodies
getElementById         52                6   -> 44 are `() => null`
createElement          51                6   -> all forward to the shim's
createElementNS        46                5      makeNode but one
querySelector           8                1   -> `() => null`
createTextNode          8                2   -> both = the shim's makeTextNode
addEventListener        5                2   -> `() => {}`
querySelectorAll        4                1   -> `() => []`
body                    4                2
```

So **42 of 54 were byte-equivalent copies** of what `installDocument`
already installs, and the 12 that were not needed exactly what the
`overrides` argument exists for: 8 a `getElementById` policy
(`nodes[id] ?? null` x3, `makeNode("div")` x3, `nodes[id] ?? makeNode`,
and the `bga-*` block map), 4 a `body` or a node factory that does more
than forward (`node.open`, `node.hidden`, `node.ns`).

**The move.** All 54 onto `installDocument`, 12 with overrides.
52 files, +166/-187.

```text
$ grep -c "globalThis.document = {" tests/unit/*.py | grep -v ':0'
(no output)
```

**One semantic change, named.** 8 `querySelector: () => null` and 4
`querySelectorAll: () => []` now get the shim's, which searches its own
body - empty in these detached-root harnesses, so the same answer. The
suite run is the measurement of that.

**Mutations.** `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` cleared.

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | a fresh hand-built `globalThis.document = {` in `test_buttons_that_know_why.py` | `test_no_harness_wires_its_own_document`, naming `installDocument` and all three defects | 1 failed, 6 passed |
| M2 | `documentElement: makeNode("html")` deleted from `tests/dom_shim.mjs` | `test_a_report_you_can_navigate.py`, 2 clauses, `Cannot read properties of undefined (reading 'dataset')` | 2 failed, 16 passed |

M2 is the one that holds the fourth bullet: `boot()`'s
`documentElement?.dataset` guard is dropped, and the shim is now what
keeps it standing.

**A defect the conversion found in itself.** The first converter took
every `makeNode` for the shim's; `test_the_views_that_draw.py` shadows
it with a wrapper setting `node.ns`, so the move would have dropped
`createElementNS`'s namespace. Caught by diffing before writing.

**Not fixed, filed as a finding.** `test_focus_is_an_investigation.py`
and the three handoff harnesses still hand-build a **node**.
`test_no_harness_builds_its_own_node` misses them: it looks for
`return {` carrying `setAttribute`, and these are
`const node = {...}; return node;`. Out of scope - this row is the
document.

**Acceptance Test, pasted:** the before/after counts above; the 50
converted files plus `test_the_dom_shim_is_one_instrument.py` green at
`-n 2`, `1024 passed, 29 skipped in 468.21s`, then the one ordering
fixup re-run green (`10 passed, 2 skipped`). `make lint` clean.

**Deviation from the Required Fix:** none. The Out of Scope held: the
shim's fidelity is untouched and no browser-tier guard was converted.
