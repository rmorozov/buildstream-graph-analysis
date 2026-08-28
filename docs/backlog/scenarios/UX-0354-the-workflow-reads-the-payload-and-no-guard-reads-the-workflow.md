# UX-354: the workflow reads the payload, and no guard reads the workflow

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-293 (the packaging step reads the contract from the tree), UX-344 (the two namespaces lifted) | **Serves:** whoever changes a contract next | **Topic:** contracts

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
