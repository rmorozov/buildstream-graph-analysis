"""UX-248: every contract this tool stamps an artifact with.

`schemas.names()` answers a narrower question than it looks like it
does — it lists the documents `bga --schema` can print, which is not
the same as the documents `bga` *writes*. Measured when this was filed:

```text
stamped somewhere in bga/ or tools/   9
schemas.names()                       7
  host/v1     defined in bga/hostinfo.py, known to one guard as a
              hand-added special case
  sources/v1  defined in bga/sources.py, written to `sources.json` in
              every run directory, read back by `load_inventory` -
              and in no registry, no guard, and no document
```

The pattern is `UX-233`'s own, one level up: a guard that names one
file will not see the second one. `_published_schemas()` unioned the
registry with a single hard-coded id, so the *third* contract defined
outside `schemas.py` joined nothing.

So this is derived rather than listed. A module that owns a contract
declares it as a module-level `SCHEMA`, and the inventory is whatever
the package actually contains — which means the next one is inventoried
by existing, not by someone remembering.

Direction 10 is what needs it: a release records a contract *set*, and
an artifact stamps the contracts it depends on. Neither is expressible
while the set cannot be enumerated.
"""
import importlib
import pkgutil
import re
from typing import Dict, List

# `analyze/v1`, `store-aggregate/v1`. The version is the whole point of
# the shape: an id with no `/vN` cannot say that it moved.
CONTRACT_ID = re.compile(r"^[a-z][a-z0-9-]*/v\d+$")

# Where a contract may be declared. A module-level `SCHEMA` string is
# the convention every module outside `schemas.py` already followed
# (`hostinfo`, `sources`) - this reads it rather than asking for a
# second declaration somewhere central.
_DECLARATION = "SCHEMA"

# `UX-297`: and the shapes a module still *reads* but no longer writes.
# A retired id is not a curiosity - an old store is full of files
# stamped with one, and the release that can read them has to be able
# to say so. Declared as a module-level tuple beside `SCHEMA`, by the
# module that owns the shape.
_RETIRED = "SUPERSEDED"

# `UX-381`: and the shapes a module *owns* without stamping on a
# document of its own. The walk below covers `bga` only - a module in
# `tools/` that declares a `SCHEMA` is invisible to it, which is
# `UX-248`'s own defect one directory over. `host-samples/v1` is
# written by `tools/bst_native_build_tracer.py` into the capture
# directory, and the module that knows that directory is `run_store`,
# so `run_store` names it. Declared as a module-level tuple beside
# `SCHEMA`, exactly as `SUPERSEDED` is.
_OWNED = "OWNED"

# `UX-540`: and the *input* shapes a module reads and nothing here
# stamps - `graph/v9`, `trace/v9`, `run-context/v9`. Not retired and
# not emitted, so neither `SUPERSEDED` nor `SCHEMA` can carry them, and
# an unregistered input is invisible to every consumer asking what a
# release accepts. Declared as a module-level tuple, by the module that
# reads the shape.
_INPUT = "READS"


def _tuple_declared(attribute: str) -> List[str]:
    """Every contract id in a module-level tuple named `attribute`."""
    import bga

    found = set()
    for module in pkgutil.iter_modules(bga.__path__):
        try:
            loaded = importlib.import_module(f"bga.{module.name}")
        except Exception:  # pragma: no cover - see `_declared_in_modules`
            continue
        for name in getattr(loaded, attribute, ()) or ():
            if isinstance(name, str) and CONTRACT_ID.match(name):
                found.add(name)
    return sorted(found)


def _declared_in_modules() -> Dict[str, str]:
    """`{contract id: owning module}` from the package itself.

    The walk costs ~3ms once `bga.cli` is loaded, which is every context
    that needs this, and ~180ms from cold. It is not on the analysis
    path: an artifact is stamped once.
    """
    import bga

    found = {}
    for module in pkgutil.iter_modules(bga.__path__):
        name = f"bga.{module.name}"
        try:
            loaded = importlib.import_module(name)
        except Exception:  # pragma: no cover - a module that cannot
            continue       # import has bigger problems than its id
        declared = getattr(loaded, _DECLARATION, None)
        if isinstance(declared, str) and CONTRACT_ID.match(declared):
            found[declared] = name
        for retired in getattr(loaded, _RETIRED, ()) or ():
            if isinstance(retired, str) and CONTRACT_ID.match(retired):
                found.setdefault(retired, name)
        for owned in getattr(loaded, _OWNED, ()) or ():
            if isinstance(owned, str) and CONTRACT_ID.match(owned):
                found.setdefault(owned, name)
    return found


def inventory() -> Dict[str, str]:
    """Every contract, mapped to what owns it.

    Two sources, because there are genuinely two kinds: the documents
    `schemas.py` publishes with view-hints and a printable JSON Schema,
    and the on-disk shapes a single module owns. Being *inventoried* and
    being *printable* are different properties, and conflating them is
    how `sources/v1` was skipped.
    """
    from . import schemas

    owned = dict(_declared_in_modules())
    for name in schemas.names():
        owned.setdefault(name, "bga.schemas")
    return owned


def ids() -> List[str]:
    """Every contract id, sorted. The set a release records."""
    return sorted(inventory())


def printable() -> List[str]:
    """The subset `bga --schema` can print.

    Named rather than assumed: a reader who meets `sources/v1` in a run
    directory and asks `bga --schema sources/v1` gets a refusal, and
    that refusal should be a documented difference rather than a
    surprise.
    """
    from . import schemas

    return sorted(schemas.names())


def superseded() -> List[str]:
    """Contracts this tool reads and no longer writes.

    `UX-297` retired the Plane 2 monolith. Every capture in an existing
    store is stamped with the shape it retired, and the reader still
    consumes it - so the id is part of what a release supports, not
    part of what it emits, and those are different facts a consumer
    needs separately.
    """
    return _tuple_declared(_RETIRED)


def reads() -> List[str]:
    """Input contracts: read by this tool, stamped by something else.

    `UX-540`: the third kind. `ids()` is what a release *emits* and
    `superseded()` what it still opens after retiring - the shapes
    `bga analyze` requires and refuses without were in neither, so
    nothing could answer which input versions a release accepts. They
    stay out of `ids()` deliberately: emitting `graph/v9` is something
    this tool has never done.
    """
    return _tuple_declared(_INPUT)


def unprintable() -> List[str]:
    """Contracts that are written but have no printable schema."""
    return sorted(set(ids()) - set(printable()))
