# UX-990: the BuildStream behaviour claims in `tools/` are outside the register `UX-940` built for `bga/`

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-940 | **Blocks:** — | **Found by:** round 138 — enumerating `bga/`'s versioned claims for `UX-940` | **Serves:** whoever reads a BuildStream behaviour claim in the capture tools and has to decide whether it still holds on the pinned binary | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`UX-940` put every BuildStream behaviour claim in `bga/` into
`tests/bst_claims.json`, each with the version it was last read on, and
its guard warns when that version is older than `ci.yml`'s
`BST_VERSION`. Its completeness clause reads `bga/` only, because
`bga/` is what the row named. The capture tools carry the same class of
claim, and none of them is in the register:

```text
$ grep -rnE "\bBuildStream 2\.[0-9]+\.[0-9]+\b" tools/ --include=*.py | wc -l
14
$ grep -rlE "\bBuildStream 2\.[0-9]+\.[0-9]+\b" tools/ --include=*.py | wc -l
8
```

Thirteen of the fourteen name 2.7.0 and one names 2.8.0; CI pins 2.8.1.
Some are behaviour claims (`bst_show_to_graph.py:127`, the only
per-element parallelism control; `bst_checkout_cost.py:18`, what
`_stream.py::checkout()` does), some are provenance of a fixture or a
log header (`bst_cache_logs.py:38`), and which is which is the reading
this row owes.

## Required Fix

Read each of the fourteen lines, register each that is a behaviour claim
with a 2.8.1 reading from that wheel, and widen the completeness clause
of `tests/unit/test_a_behaviour_claim_names_the_bst_it_was_read_on.py`
to `tools/`, with a way to say a line is provenance rather than a claim.

## Out of Scope

`tests/`'s fixture provenance (`bst 2.7.0` logs, a `toolchain` block),
which records what a fixture was captured with and does not age.

## Acceptance Test

The completeness clause reddens on a new versioned line in `tools/` that
is neither registered nor declared provenance, and every registered
`tools/` claim carries a reading pasted with its command.

## Decision

The `architect`, round 140, at `398b4db9`.

```text
Route:     read each of the 14 tools/ lines in the downloaded 2.8.1 wheel; register the claims in
           tests/bst_claims.json with provenance lines (path, anchor, reason) in the same
           register, not source markers; widen completeness to bga/ and tools/, per line
Rejected:  keep it in the bookkeeping batch - each line needs its own wheel reading, and a
           wrong claim is a wrong capture: product work
           a `# provenance` source marker - changes tools/ files under the sizes ratchet
Files:     tests/bst_claims.json, tests/unit/test_a_behaviour_claim_names_the_bst_it_was_read_on.py
Guard:     test_every_versioned_line_in_bga_and_tools_is_registered_or_provenance
Mutation:  add a "BuildStream 2.8.1" line to the registered tools/bst_show_to_graph.py -> red,
           which today's per-file check would not (measure bga/ per line first: 7 vs 16 anchors)
Class:     product
```

## Outcome
