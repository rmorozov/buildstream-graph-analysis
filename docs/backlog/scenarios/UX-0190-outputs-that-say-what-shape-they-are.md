# UX-190: outputs that say what shape they are

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-75 (the published-contract precedent), UX-171 (`sources/v1`, the one output that already does this) | **Topic:** contracts

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

## What was built

**1. Every JSON output self-declares**, with `schema` as its *first*
key - so a consumer reading the head of a streamed or truncated
document learns what it is before it reads anything it has to
interpret:

```text
$ bga analyze RUN/ --format json | head -3
{
  "schema": "analyze/v1",
  "run_id": "golden-fixture-manifest-hash-v1",
```

`analyze/v1`, `compare/v1`, `blast/v1`. The golden snapshot regenerated
for exactly two additive lines (`schema`, `section`), which is the
whole diff.

**2. `--schema` on each command** prints the JSON Schema and exits 0.
It is a pre-parse hook rather than a registered flag, for two reasons:
it must not require the run directory the command otherwise needs - it
answers about a *shape*, not about a run - and it runs before the
`UX-67` alias dispatch, which would otherwise hand `bga doctor
--schema` to a tool that has never heard of the flag. A command with no
versioned JSON output says so and exits 2.

**3. One source of truth.** `bga/schemas.py` is what the renderers
stamp with and what `--schema` prints, so the schema cannot be a
hand-written copy drifting from the payload.

**4. The round-trip guard**, which is the point of the item: the golden
run's real `--format json` output is validated against the schema
`bga <cmd> --schema` really prints, for all three commands, with
`jsonschema` as a **dev** dependency only - the runtime emits the key
and never validates.

**The versioning rule** - a rename or removal bumps, an addition does
not - is in the module, in the fixing guide's checklist (item 6, where
the next fixer will meet it), and in the spec's new **Part 32.5**,
which lists the three output schemas beside the input ones.

### Where the guards divide the work, and why

`analyze` is the one output with a variable key set: a section
subcommand (`bga floors`, `bga graph`) emits the same document
restricted to its own keys, and `findings` is omitted rather than empty
when there is nothing to conclude. So its schema requires only what
every analyze document carries, plus a new `section` key naming the
restriction - which is precisely what lets a consumer tell "this is
`bga floors`" from "the field was removed".

The rest is covered by two other pins, and a test asserts *which guard
catches what* so neither is mistaken for the other:

| what changes | what fails |
|---|---|
| a required key removed or renamed | the round-trip validation |
| an optional `analyze` key renamed | `ANALYZE_FULL_KEYS` |
| a new top-level key added | nothing (by design) - but the pin's reverse direction asks you to list it |
| a `required` entry *deleted from the schema* to make a test pass | the loosening guard |

That last row was found by mutation: deleting `verdict` from compare's
required list reddened nothing, because validation only checks the
payload against the schema and never the reverse. The mirror guard
asserts every key the real payload emits is either required or named
as conditional.

Tests: 25 new (`tests/unit/test_output_schemas.py`), all driving the
real CLI through a subprocess. Five mutations, each red.

