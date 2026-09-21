# UX-909: the documentation guard cannot see a published block's own keys

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-628, UX-655, UX-866 | **Found by:** architecture review 25 (2026-09-20) — `UX-891` added five `floors` keys to `analyze/v6` and no clause went red, because the walk that defines the guard's population never descends into a top-level object | **Serves:** R1 and R3, who read `floors` and `attribution` before anything else in the report and have only the documents to read them by | **Topic:** guards | **Area:** bga | **Shape:** judgement

## Motivation

`tests/unit/test_the_documents_keep_up_with_the_contracts.py` is the
gate that says a consumer-facing key is named in a document outside the
backlog. Two things bound its population, and both are wider than the
guard's own argument.

**The walk stops above the block.** `_consumer_surface()` takes each
printable schema's top-level properties plus every *row* it hands over.
A top-level object that is a published block of scalars is neither, so
its children are outside the population:

```text
$ python3 - <<'PY'
import importlib.util
s = importlib.util.spec_from_file_location(
    "g", "tests/unit/test_the_documents_keep_up_with_the_contracts.py")
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
from bga import contracts, schemas
surface = m._consumer_surface()
missing = {f"{k}.{sub}"
           for name in contracts.printable()
           for k, p in (schemas.schema(name).get("properties") or {}).items()
           if isinstance(p, dict) and (p.get("type") == "object" or "properties" in p)
           for sub in (p.get("properties") or {}) if sub not in surface}
print(len(missing), "certified_headroom" in surface)
PY
302 False
```

This is the third turn of one shape. `UX-838` (review 23) found
`additionalProperties`-shaped rows invisible to both of `_row_keys`'s
cases; `UX-866` (review 24) found `run_instance` invisible because it is
typed as a bare `object`, and bought back one case with `_hint_keys`.
Each time the population was widened by the exact shape that had just
escaped it. A top-level object of scalars is the next shape, and buying
it back one at a time is what keeps producing the next one.

`certified_headroom` — the number the Key Findings block leads with —
has never been in the population. Neither were `lb_cpu_us`,
`lb_cpu_coverage`, `lb_cpu_governing_cores`, `lb_cpu_cores_source` and
`lb_cpu_binds` when they shipped; a human review caught them, which is
the failure mode `UX-628` filed this guard to end.

The docstring argues the walk is deliberately partial — "most of them
internal shapes of one block". That argument holds for
`blast_radius_distribution.deciles`. It does not hold for `floors`,
`attribution` and `cache`, which are not internal shapes of a block:
they *are* the report's blocks, and a reader meets their scalars
directly.

**The exclusion list names paths, not arguments.**
`_named_in_the_documents()` skips `docs/backlog/` and `docs/audits/`
because "a task file naming the key it added is the argument, not the
document". A design document carrying `**Status:** proposed` is the
same thing and is not skipped:

```text
$ grep -m1 '^\*\*Status:\*\*' docs/design/in-step-parallelism.md
**Status:** proposed — an argument, not a numbered Direction and not a
```

Nothing rests on it alone today (measured: 0 surface keys documented
only by a proposed design document, after `UX-891`'s round), so this
half is latent. It is the same population question, and filing it apart
would split one fix in two.

## Required Fix

Widen `_consumer_surface()` to descend one level into a top-level
object whose children are scalars — the published-block shape — while
leaving the deep recursive key set out, which `UX-384` banned from the
inventory for a reason. Whatever the boundary becomes, the guide's
"Which keys the prose names" section states it, because that section is
what a reader trusts when the guard is green.

Then take the resulting backlog of newly-visible-and-undocumented keys
as a reading, not a fix: name them, or argue in this task's Outcome why
a key the walk now reaches is not one a document should carry.

Second, skip a `docs/design/*.md` whose header declares
`**Status:** proposed`, on the same argument the backlog exclusion
already makes.

## Out of Scope

The full recursive key set (`UX-384`). Changing any schema. Documenting
keys the widened walk does not reach.

## Acceptance Test

A mutation that adds a scalar key to `floors` in `bga/schemas.py`, with
no document naming it, reddens
`test_the_documents_keep_up_with_the_contracts.py`; the same mutation is
green on `main` today. And a mutation that moves an existing key's only
mention into a `**Status:** proposed` design document reddens it too.

## Outcome

**The gap, measured.** The filing said 302 keys outside the population;
at `70765b0` it is **305**, and `certified_headroom` — the number Key
Findings leads with — was not in it:

```text
$ python3 - <<'PY'   # the filing's own probe, re-run
filed measurement: 305 certified_headroom in surface: False
surface size: 313
PY
```

**The boundary, and why it is not the one the Required Fix worded.**
The fix asked for "a top-level object whose children are scalars". That
is a fifth *shape*, and the Motivation's own argument is that buying
shapes back one at a time is what produces the next one — `UX-838`'s
`additionalProperties` row, `UX-866`'s bare `object`, this row's block
of scalars. It also excludes `cache`, which the Motivation names as one
that must be reached, since four of its eleven children are objects. So
the walk takes a **depth** instead: every key declared one level below a
top-level property, whatever shape it is. `_block_keys` is eight lines
and has no cases. The deep set stays out, which is `UX-384`'s ban and
the line the guide now states: `blast_radius_distribution.deciles` is in
the population and its own nine buckets are not.

**The close, measured.** The surface goes 313 → **562 keys**, and the
undocumented register stays at zero because all of them were named:

```text
$ pytest tests/unit/test_the_documents_keep_up_with_the_contracts.py
before documenting: 153 published key(s) no document names
after:              29 passed
```

**The backlog, read rather than argued.** All 153 are in
`docs/guides/cli.md`'s new `### Inside a published block (UX-909)`,
grouped by the block that publishes them, one line each. **None was
argued out** — the register is still `frozenset()`. 352 of the 362
block children carry a schema `description`, so the rows are condensed
from the schema rather than invented; the ten without were read at the
site that computes them.

**The second half stopped being latent.** The filing measured 0 surface
keys resting only on a `**Status:** proposed` design document. With the
widened walk there are **four** — `mean`, `skipped_inputs`,
`t_infinity_cold`, `unmeasured_processes` — so the exclusion is load
bearing now rather than a matching argument. The subject is the
**header**, what precedes the first `## `: `directions.md` gives each
numbered Direction its own `**Status:**` line, and a landed document
must not become proposed because one section inside it is. That is
asserted, not assumed.

**The mutation table.** Applied, confirmed landed, guard watched red for
the right reason, reverted, watched green:

| mutation | guard |
|---|---|
| a scalar added to `floors` in `bga/schemas.py`, no prose | red — `test_a_new_key_with_no_prose_reddens_naming_the_key`, naming `zz_floors_probe`; **green on `main`'s own guard**, which is the Acceptance Test's other half |
| `mixes`'s only mention moved into `in-step-parallelism.md` | red — same clause, naming `mixes` |
| `_block_keys` stops descending | red — `test_a_scalar_of_a_published_block_is_in_the_population` |
| `_block_keys` recurses past one level | red — `test_the_walk_stops_one_level_below_a_top_level_property` |
| the proposed-design clause returns `False` | red — `test_a_proposed_design_document_does_not_document_a_key` |

**The deviation.** Beyond the boundary above: the guide's coverage
section now states the depth rule and the proposed-design exclusion,
and both figures in it (`562 keys`, `0 undocumented keys`) are read off
the walk and the register rather than typed, so the next widening moves
the guide or reddens.
