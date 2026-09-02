# UX-537: the three contracts `bga` reads and never registers

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-248` (the contract inventory this extends), `UX-381` (the capture layout that names them), `UX-520` (the bundle that hit it) | **Found by:** `UX-520`, building the run bundle | **Serves:** anyone asking what shapes a release can read | **Topic:** contracts

## Motivation

`bga.contracts` derives the contract set from the package: a module
declares `SCHEMA`, `SUPERSEDED` or `OWNED`, and the walk inventories it.
That covers every shape `bga` **stamps**. It covers none of the shapes
`bga` only **reads**.

Measured while `UX-520` was built:

```text
$ python3 -c "from bga import contracts, run_store; \
  layout = {c for _p,_pr,c,_w in run_store.CAPTURE_LAYOUT if c}; \
  print(sorted(layout - set(contracts.ids()) - set(contracts.superseded())))"
['graph/v9', 'run-context/v9', 'trace/v9']
```

Those three are the *inputs* — the declared element graph, the
scheduler's spans, and what the run was. They are required members of
`capture-layout/v1`, they are named in specification Part 32.6's table,
`bga analyze` refuses without them, and `bga.contracts` does not know
they exist.

`UX-520` hit it as a live refusal: `bga bundle --load` derived its
readable set from `contracts.ids() | contracts.superseded()`, and the
first real bundle of a healthy capture was declined for carrying all
three. The workaround there is to union in the contracts
`CAPTURE_LAYOUT` names, which is correct for that command and leaves
the registry still wrong for everyone else.

This is `UX-248`'s own defect one direction over. That item found the
inventory covering only what `schemas.py` published and fixed it by
deriving from the package; the derivation still only sees *writers*, so
a shape nothing writes joins nothing — no `bga --schema`, no release
contract set, no line in Part 32.5, and no way for a consumer to ask
which input versions a release accepts.

## Required Fix

- The three input contracts are declared by the modules that read them,
  by the same `SCHEMA`-beside-the-constants convention, and appear in
  `contracts.ids()` — or, if "read but never written" is a third kind
  rather than a fourth declaration, a `READS` tuple that
  `bga.contracts` walks alongside `SUPERSEDED` and `OWNED`.
- The distinction stays visible: a consumer must still be able to ask
  which contracts a release *emits* as against which it *accepts*.
  `superseded()` already carries "read, never written" for retired
  shapes and these are not retired, so the answer is probably a new
  accessor rather than a wider `ids()`.
- Whatever the registry gains, the guards that hold the documents to it
  (`test_the_documents_keep_up_with_the_contracts.py`,
  `test_the_front_door_is_current.py`) keep passing, which means Part
  32.5, the architecture inventory and `docs/README.md` each gain the
  three rows or state the exemption.
- `bga.bundle.readable_contracts()` drops its `CAPTURE_LAYOUT` union and
  reads the registry, since that union exists only for this gap.

## Out of Scope

- Versioning the input shapes differently, or moving any of them. This
  is about the registry knowing what already exists.
- `analysis/v9`, which specification 32.5's opening block names beside
  the three and which may be a fourth instance or may be a stale id —
  measure before assuming.

## Acceptance Test

`contracts` answers for `graph/v9`, `trace/v9` and `run-context/v9`,
pasted; the three documents that must name a contract each name them,
pasted; and `bga.bundle.readable_contracts()` returns the same set it
returns today with its `CAPTURE_LAYOUT` union removed — pasted both
ways, because a round-trip that starts refusing healthy captures is the
regression this must not cause.

## Outcome

_Not started._
