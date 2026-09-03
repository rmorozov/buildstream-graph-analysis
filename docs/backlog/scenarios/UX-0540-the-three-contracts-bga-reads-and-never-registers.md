# UX-540: the three contracts `bga` reads and never registers

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-248` (the contract inventory this extends), `UX-381` (the capture layout that names them), `UX-520` (the bundle that hit it) | **Found by:** `UX-520`, building the run bundle | **Serves:** anyone asking what shapes a release can read | **Topic:** contracts

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

**Round 81, 2026-09-03.** A third kind: `READS`, walked beside
`SUPERSEDED` and `OWNED`, answered by `contracts.reads()`. `ids()` is
unchanged at 23 — emitting `graph/v9` is something this tool has never
done.

**The gap, before:**

```text
$ python3 -c "from bga import contracts, run_store; \
  layout = {c for _p,_pr,c,_w in run_store.CAPTURE_LAYOUT if c}; \
  print(sorted(layout - set(contracts.ids()) - set(contracts.superseded())))"
['graph/v9', 'run-context/v9', 'trace/v9']
```

**Closed:**

```text
contracts.reads()         ['graph/v9', 'run-context/v9', 'trace/v9']
len(contracts.ids())      23
len(contracts.superseded()) 9
layout - ids - superseded - reads: []
readable_contracts() now    26
with the CAPTURE_LAYOUT union 26
identical: True
```

The three documents, one row each: `specification.md:1695`,
`architecture.md:993`, `docs/README.md:111` (the `graph/v9` row; the
other two beside it).

**`analysis/v9` — measured, not fixed.** Neither a fourth instance nor
a stale id: it is `bga.ingest.models.AnalysisResult`, the analyzer's
in-memory result shape (spec 32.4). The string is a literal nowhere in
the tree, no artifact carries it, no loader parses it, and it reaches a
consumer only as `analyze/v5`. Part 32.5 now says so.

**Mutations verified red and reverted (13):** `READS` drops `trace/v9`
(6 guards, incl. the two that used to hard-code the three); the bundle
stops reading `reads()` — `UX-520`'s own regression; `READS` declared
on `run_store` instead of the reading module; the `graph/v9` row cut
from 32.5, and the whole input table; the `trace/v9` row cut from the
architecture chapter; a `probe/v1` row added to it; `run-context/v9`
misspelled in the index; `reads()` folded into `ids()`; `trace/v9`
declared retired as well; the `analysis/v9` verdict deleted from 32.5;
`analysis/v9` declared an input; `CAPTURE_LAYOUT` citing `probe/v1`.

**A guard of mine that did not discriminate.**
`test_part_32_5_names_every_input` first read the whole of Part 32.5
and stayed **green** when the `graph/v9` row was deleted — the
paragraph that argues for the table names all three ids, so the guard
matched its own explanation (`falsify`, failure mode two). It reads
only the rows of the input table now, and both mutations redden it.

**Deviation from the Required Fix:** none. The Fix offered `ids()` or a
`READS` tuple; `READS` was taken, because the same section requires
emits and accepts stay separable.

**Tier:** `make test-touching` — 12 files, 318 passed, 3 skipped,
31.71s. `make lint` clean. New file
`tests/unit/test_the_registry_knows_what_it_reads.py` (13 tests,
0.25s) needs a **small** tier row; the orchestrator owns `tests/tiers.py`.
Full suite is the orchestrator's gate.
