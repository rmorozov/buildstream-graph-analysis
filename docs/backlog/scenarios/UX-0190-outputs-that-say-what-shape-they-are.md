# UX-190: outputs that say what shape they are

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-75 (the published-contract precedent), UX-171 (`sources/v1`, the one output that already does this)

## Motivation

Field feedback: *"our analyze schema and other schemas evolved
considerably — maybe it's good idea to update them and have a command
line switch [to] output schemas [the] tool support[s] and produce[s] —
this can be later used to visualize json report."* Round 20
ground-truthed it: **input** formats are spec'd (`run-context/v9`,
`graph/v9`, `trace/v9` in Part 32; `sources/v1` self-declares and is
checked on load) — but the **output** JSON of analyze, compare and
blast carries no `schema`/version field, has no schema file anywhere
in the repo, and its only guards are prose-consistency tests. The
drift is not hypothetical: this very range renamed a published compare
field (`runs_outside_band` → `edges_outside_band`) with nothing to
signal it to a consumer.

## Required Fix

1. **Every JSON output self-declares**: `"schema": "analyze/v1"`
   (compare/v1, blast/v1) as the first key — versioned from today's
   shape, with the fixing-guide gaining the rule that a
   field rename or removal bumps the version and a addition does not
   (the usual contract).
2. **`--schema` on each command** prints the JSON Schema of its
   output and exits 0 — generated from one source of truth per
   command (a schema module the renderer is built against, not a
   hand-written copy), so the schema cannot drift from the payload
   without a test noticing.
3. **A round-trip guard per command**: the golden run's JSON output
   validates against its own `--schema` (jsonschema as a dev
   dependency only — the runtime never validates, it just emits).
4. The spec's Part 32 gains the three output schemas beside the input
   ones, generated or referenced — one home, per the canonical-home
   rule.

## Out of Scope

- The visualization itself (the schema is its enabler; the user named
  it as "later").
- Versioning the text reports (prose is not a contract).

## Acceptance Test

`bga analyze --schema | python -m jsonschema ...` accepts the golden
run's `--format json` output for all three commands; removing a field
from the payload without touching the schema reddens the round-trip
guard; the `schema` key is the first key of each payload; the docs
name the versioning rule. `edges_outside_band` appears in compare's
schema with a note dating the rename.
