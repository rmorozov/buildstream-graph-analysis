# UX-937: the area vocabulary is read from the fixing guide's tree by a regex that admits only two of its three top-level directories, so no row can declare `tests`

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-688 | **Blocks:** — | **Found by:** round 137 — `UX-925`'s close put three new skip reasons in `tests/conftest.py` and a new guard file in `tests/unit/`, and there was no area to declare for either | **Serves:** every row whose change lives under `tests/`, and the area pages that are meant to say where work lands | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`UX-688` made the area vocabulary a derivation on purpose, and says
why in `tools/dev_close_task.py`:

> the areas are the module tree the fixing guide's §6 already
> maintains, read from it rather than typed here — a second list of
> directories is a second list to drift.

`declared_areas()` then reads §6 with this:

```python
found = {m.rstrip("/") for m in re.findall(
    r"^((?:bga|tools)/[a-z_]+/)", section, re.M)}
return found | {"bga", "tools", "bga/viewer", AREA_UNKNOWN}
```

The alternation is the second list. §6's tree names **three** top-level
directories and the regex admits two of them, so the derivation reads
a proxy for the tree rather than the tree — fixing guide §5, in the
instrument built to stop exactly that. The vocabulary it produces:

```text
$ python3 -c "from tools import dev_close_task as d; print(sorted(d.declared_areas()))"
['bga', 'bga/attribution', 'bga/diagnostics', 'bga/floors', 'bga/graph',
 'bga/ingest', 'bga/normalize', 'bga/occupancy', 'bga/replay', 'bga/report',
 'bga/structural', 'bga/utilisation', 'bga/validation', 'bga/viewer',
 'tools', 'tools/native_trace', 'unassigned']
```

§6 names `tests/unit/`, `tests/tiers.py`, `tests/conftest.py`,
`tests/ci_reference.json` and `tests/touch_map.json` — and `tests/`
is the repository's largest surface at 580 test files, against 493
unit files' worth of modules under `bga/` and `tools/`. A row whose
change lives entirely there has one spelling available: `unassigned`,
which is documented as the bucket for rows that touch **no code at
all**.

```text
$ python3 -c "...Counter(d.file_areas().values())"
tools 235 · bga 107 · bga/viewer 102 · unassigned 63 · tools/native_trace 10 · ...
```

So the 63-row bucket `UX-501` says "shrinks as rounds classify"
cannot shrink for a test-only row, because there is nothing to
classify it as. A guard-only round — and this repository closes them
regularly — is indistinguishable in the index from a round that
touched no code.

## Required Fix

Read §6's tree for what it lists rather than for what the regex
expects: any top-level directory the tree names, with its
subdirectories, is an area. `tests` and `tests/unit` fall out of that
without being typed anywhere, and so does the next directory §6
grows.

The area pages under `docs/backlog/areas/` are derived, so a new area
appears there on the next `dev_close_task.py --check --write`.
Reclassifying any of the 63 existing `unassigned` rows is a judgement
call per row and is not this row's work.

## Out of Scope

Reclassifying existing rows. The `unassigned` bucket itself, which
stays for rows that touch no code and for rows naming two areas at
once (`UX-501`). Whether `examples/` or `docs/` should also be areas —
§6's tree is the answer to that, whatever it says, and this row only
asks that the reader believe it.

## Acceptance Test

`declared_areas()` contains `tests` and `tests/unit`, and a task file
declaring `**Area:** tests` passes `dev_close_task.py --check`'s
"every declared area is one the fixing guide's §6 tree knows"
property, which reds today.

Two mutations, each applied, reddened, reverted:

- delete the `tests/unit/` line from §6's tree — `tests/unit` must
  drop out of the vocabulary, or the reader is still typing the list
  it claims to derive;
- add a line for a directory that does not exist to §6's tree — the
  vocabulary takes it, which is the same trust the two existing
  top-level entries already get, and the guard that reads §6 against
  the real tree (`test_the_context_map_is_the_tree.py`) is what
  catches it.

The first is the one that discriminates: a fix that hard-codes
`tests` beside `bga` and `tools` passes the acceptance sentence and
fails this mutation.

## Outcome
