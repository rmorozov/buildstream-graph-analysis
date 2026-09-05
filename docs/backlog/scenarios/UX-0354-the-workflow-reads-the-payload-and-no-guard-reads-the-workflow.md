# UX-354: the workflow reads the payload, and no guard reads the workflow

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-293 (the packaging step reads the contract from the tree), UX-344 (the two namespaces lifted) | **Serves:** whoever changes a contract next | **Topic:** contracts | **Area:** tools

## Motivation

Twice now, a deliberate contract change has been discovered by a red
pull request rather than by the suite, in the same file both times.

`UX-288` bumped `analyze` to v2 and `.github/workflows/ci.yml`'s
packaging step asserted the version literally, so it went red. `UX-293`
fixed that half by reading `ANALYZE` out of `bga/schemas.py` instead of
pinning it, and wrote the reason down:

> the one file the suite does not scan

The other half of the same assertion stayed a literal:

```yaml
assert d.get('signals'), 'the payload has no signals'
```

`UX-344` lifted `signals` away. Every guard in the suite passed - 4,440
of them - and the failure appeared on the pull request:

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
AssertionError: the payload has no signals
##[error]Process completed with exit code 1.
```

Fixed in the same round by reading `ANALYZE_FULL_KEYS` from the
*installed* package, which is what that job is testing. But the fix is
the second instance of one gap: **the workflows make claims about the
payload's shape, and nothing in the suite reads the workflows.** A
third assertion of the same kind added tomorrow would be found the same
way, and the tool's own rule is that a claim nobody can check is not a
contract.

The two mechanical inventories that make this checkable already exist:
`schemas.names()` for contract ids and `ANALYZE_FULL_KEYS` for
always-present keys. There are three workflow files, and one line
between them reads a payload today.

## Required Fix

A guard walks `.github/workflows/*.yml` and fails when a step names a
published contract id or a top-level payload key as a literal - the
same property `UX-293` argued for the version, applied to the whole
file rather than to the one expression that had already broken. A
workflow that needs the value reads it from the tree or from the
installed package, both of which the packaging step now does.

## Out of Scope

- The prose comments in the workflows, which name `signals` and
  `structural` as history. A comment recording why a step exists is
  not a claim about today's payload.
- Extending the guard to every string in the workflows. What is being
  guarded is the *payload contract*, not shell hygiene.

## Acceptance Test

Reintroducing `assert d.get('signals')` into `ci.yml` reddens a test in
`make test`, naming the file and the line - so the next contract change
is caught where every other one is, before the pull request.

## Outcome (round 54, 2026-08-28) — 🟢 Done

### The gap, measured

The two literals, and what they were:

```text
ci.yml:208                   d['schema']                    a published key
ci.yml (before the CI fix)   d.get('signals')               a key UX-344 removed
real-project-capture.yml:741 json.load(...)["members"]      the set document's shape
                             m["run_dir"]
```

Both files, zero guards. `make test` was green for the whole round
that broke the first one.

### The rule, and the two shapes it has

A step that **parses** a JSON document this repository produces must
not name that document's keys. Two rules, because one shape does not
cover both defects:

- **Shape.** A string literal standing where a key goes -
  `d['k']`, `d.get('k')`. This catches a key the package has never
  heard of, which is the case the item was filed on: after `UX-344`,
  `signals` is not in any inventory a guard could consult.
- **Membership.** Any quoted string in a parsing block that the
  package publishes - `contracts.ids()`, `ANALYZE_FULL_KEYS`, and
  every declared property of every live contract. This is `UX-288`'s
  half: its defect was `key = 'schema'`, a plain assignment with no
  subscript in it.

A third clause reads whole files rather than parsing blocks, for a
contract id anywhere - a `grep -q "analyze/v4"` is the same defect
somewhere the block rule does not look.

**What it deliberately does not guard.** Prose. Both workflows name
`signals` and `structural` in comments, as history, and a comment
recording why a step exists is not a claim about today's payload.
Comment text is stripped before matching, and crudely: a `#` inside a
string trims the rest of the line, which loses a finding rather than
inventing one. For a guard over a file nobody else reads, that is the
right direction to be wrong in.

### Both sites, now indirect

`ci.yml` reads `schemas.VERSION_KEY` beside the `ANALYZE_FULL_KEYS` the
CI fix already gave it. `real-project-capture.yml` calls
`bst_baseline_set.trend_order`, new here - the module that *writes* the
baseline set, reading it back - which also lifts the ordering rule out
of a shell one-liner into a function a test can reach:

> `bga baseline` returns newest first, because a reader asking "what is
> the baseline" wants the most recent at the top, and a trend reads
> forwards in time.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `f48b797`.

| # | mutation | reddened |
|---|---|---|
| P1 | `assert d.get('signals')` back in the packaging step — the acceptance, verbatim | `test_no_parsing_step_names_a_key_itself` — *"ci.yml:210  'signals'"* |
| P2 | `key='schema'` instead of `schemas.VERSION_KEY` | the same clause — *"ci.yml:208  'schema'"* |
| P3 | the baseline step reaches into the set document again | the same clause, twice — *"real-project-capture.yml:743  'run_dir'"*, *"'members'"* |
| P4 | `grep -q "analyze/v4"` added to a step | two clauses, including `test_no_step_spells_a_contract_id` |

**P2 is the reason the guard has two rules.** It passed the first
version of this file — `key='schema'` is an assignment, and the shape
rule only sees subscripts. The membership rule exists because that
mutation survived, not because it was designed in.

### Deviation from the Required Fix

- The filing said "a top-level payload key". The membership rule uses
  *every* declared property of every live contract, not only the top
  level: a nested key is as much the producer's to publish, and
  restricting the set would have been a narrower guard for no reason
  the filing gives. Nothing in the workflows names one either way, so
  the widening costs nothing today.
- `bst_baseline_set`'s document is not a published contract - it
  carries no `schema` stamp, and `contracts.ids()` does not know it.
  It is fixed here anyway, because the shape rule is about *who owns
  the keys* rather than about contract status, and the same
  one-liner would have broken the same way.
