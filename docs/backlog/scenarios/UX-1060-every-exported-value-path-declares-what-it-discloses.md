# UX-1060: every exported value path declares what it discloses

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 3; the owner's review on #298, finding 1, and its follow-up at `8c3bead1`, finding 1 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** contracts | **Area:** bga | **Shape:** mechanical

## Motivation

An anonymized export needs the class of every value it carries.
`bga/schemas.py` cannot hold it: it pins only the output documents'
top-level keys, sets `additionalProperties` true, and is not the schema
of `graph.json`, `trace.json`, `run-context.json` or the other
captured inputs, so a guard over it passes beside an unclassified field.

## Required Fix

A new `bga/disclosure.py` holds one policy per exported member, keyed by
the member's contract version (`graph/v9`, `trace/v9`,
`run-context/v9`, `plane2/v3`, `sources/v1`, `host-samples/v1`) or,
for an uncontracted member, its layout path. Each policy names every
value path with one of the eight classes of the design's section 3,
including map keys that are data (`per_element.<key>` is class A) and
array items. Each class B path also carries a value allowlist and its
fallback (a `b-` pseudonym for a binary name or a toolchain's tool name,
else refuse), because a public path can hold a private value. A walker returns the paths a document holds that the policy
does not name; an unknown contract version returns the whole member.

## Out of Scope

Transforming values - that is UX-1062.

## Acceptance Test

`tests/unit/test_every_exported_value_path_declares_what_it_discloses.py`
walks every member of every fixture under `tests/fixtures/` and reds on
any unnamed path. Mutations: add a key to a fixture's `run-context.json`,
and it reds naming the path; set a class B path's value to one not on
its allowlist where the path has no fallback, and it reds naming the
value; bump a member's contract version, and the
whole member is reported.

## Outcome

**Gap measured** at `9ec24dd0`: no disclosure policy anywhere.
`git grep -il disclos -- bga` hits two comments (`schemas.py:979`,
`viewer/chapters.js:588`), neither a classification; 47 transform
members across 14 fixtures (`tests/fixtures/`) had no class on any path.

**Close measured.** `bga/disclosure.py`: 14 layout members with a
treatment (8 transform, 6 drop, stage 4's table), 8 policies, 280 value
paths, 19 vocabularies (7 with a `b-`/regex fallback kept as `b-`, the
rest refuse):

```text
graph/v9 11 {'A': 4, 'B': 2, 'C': 3, 'E': 2}
trace/v9 10 {'A': 1, 'B': 4, 'C': 2, 'E': 1, 'H': 2}
run-context/v9 67 {'A': 6, 'B': 13, 'C': 33, 'D': 7, 'E': 3, 'F': 1, 'H': 4}
sources/v1 8 {'A': 3, 'B': 4, 'F': 1}
host-samples/v1 21 {'B': 2, 'C': 16, 'H': 3}
plane2/v3 155 {'A': 24, 'B': 5, 'C': 109, 'F': 17}
plane2-resource.json 2 {'C': 2}
element-slice.json 6 {'A': 1, 'C': 5}
```

`python3 -m pytest tests/unit/test_every_exported_value_path_declares_what_it_discloses.py -q`:
`62 passed in 0.27s` (47 fixture members walked, 15 walker and table checks).

The guard caught one fixture drift on its first run:
`one_source_many_elements/run/sources.json` carries `keying: "url"`,
which `bga.sources.keying_of` never writes; admitted in the `keying`
vocabulary with a comment rather than editing the fixture.

Paths are named from the fixtures plus the producer shapes read in
`tools/bst_native_build_tracer.py` for blocks the fixtures hold empty;
a real capture's block the fixtures do not hold (e.g. plane2
`resource_pressure`) is unnamed and refuses, fail closed. Every `note`,
`disclaimer`, `evidence`, `reason`, `cmd` and `signature` is class F,
not B: an allowlist of `bga`'s own sentences would restate the tracer's
literals.

**Mutations**, each applied to a copy-backed file, run, reverted, 62 green after:

| mutation | reddened | count |
|---|---|---|
| `host_cpu/run/run-context.json` gains `"codename"` | fixture walk names `codename: not named by the policy` (+ 2 walker tests reading that fixture) | 3 failed, 59 passed |
| `host_cpu/run/graph.json` `element_kind` `import` -> `acme_private_kind` | `elements[].element_kind: value 'acme_private_kind' is not on its allowlist` | 1 failed, 61 passed |
| `run_store.CAPTURE_LAYOUT` `run-context/v9` -> `v10` | 14 fixture members `<member>: 'run-context/v10' has no disclosure policy` + treatment table | 15 failed, 47 passed |
| `TREATMENTS` loses `element-slice.json` | `test_every_layout_member_states_its_treatment` | 1 failed, 61 passed |
| `_walk_map` unnamed-key `yield` -> `pass` | `test_an_added_key_is_named_by_its_path` | 1 failed, 61 passed |
| `_refused` drops `and vocab.fallback is None` | `test_a_class_b_value_with_a_fallback_is_not_refused` | 1 failed, 61 passed |
| `gaps` unknown-contract branch returns `[]` | `test_an_unknown_contract_version_reports_the_whole_member` | 1 failed, 61 passed |
| `"foundation[]": "A"` -> `"Z"` | `test_every_class_names_one_of_the_eight_or_a_vocabulary` | 1 failed, 61 passed |
| `cc1plus` off `_BINARIES` | `test_a_fallback_vocabulary_keeps_public_values_and_only_those[binary-cc1plus-True]` | 1 failed, 61 passed |
| test selects `DROP` members, not `TRANSFORM` | `test_the_fixtures_hold_every_contracted_transform_member` (+ 4 drop members with no policy) | 5 failed, 14 passed |

**Session decision.** `note`, `disclaimer`, `evidence`, `reason`, `cmd`
and `signature` are class F, not B: a fixed `bga`-authored sentence
could later be allowlisted into class B, but nothing here does that yet.
