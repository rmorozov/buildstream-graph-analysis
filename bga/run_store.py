"""UX-126: a project-local store, so the loop stops being clerical.

The documented local loop is three commands and five user-invented
paths, with the project repeated in two of them — and then the loop's
whole point, *did my change help?*, needs the user to have parked the
previous run somewhere and to type both paths into `bga compare`.

Nothing there is hard. Everything there is clerical, and the clerical
part is exactly what a user gets wrong at 6pm: `/tmp/run` against
`/tmp/run2`, yesterday's `plane2.json` joined to today's run — mistakes
the refusals catch *after* a thirty-minute build. Three audit rounds ran
this loop dozens of times and every path in every invocation was
invented by the operator.

So: `.bga/runs/<UTC-stamp>-<short-id>/` under the project, holding the
same shape the published capture refs already use, and `@last` / `@prev`
/ `@<stamp-prefix>` as ways of *naming* one. The store is a resolution
convenience and nothing more — it introduces no new format, no new
identity, and no new comparability rule. An explicit path keeps working
everywhere it worked before, and a directory that happens to be a run
directory is still one.
"""
import json
import os
import re
from datetime import datetime, timezone
from typing import List, Optional

STORE_DIRNAME = ".bga"
RUNS_DIRNAME = "runs"
CONFIG_NAME = "config"

# `@last`, `@prev`, `@20260819T134500` - the whole alias grammar. A bare
# `@` is not one, so a path that starts with `@` and is not an alias
# still reaches the filesystem and fails with its own error rather than
# a store one.
_ALIAS = re.compile(r"^@(last|prev|[0-9TZ-]{4,})$")

# The stamp is the sort key, so it has to sort lexicographically in time
# order and carry no separator that a shell would need quoting for.
_STAMP = "%Y%m%dT%H%M%SZ"


class StoreError(Exception):
    """Something the user asked for by name is not there.

    Distinct from a missing *path*, because the remedies differ: a bad
    path is a typo, and a missing `@prev` means "you have only ever taken
    one snapshot here".
    """


def project_root(start: Optional[str] = None) -> Optional[str]:
    """The nearest enclosing BuildStream project, or `None`.

    Walks up from `start` looking for `project.conf`, the same marker
    `bga cache-logs` uses (`UX-127`). Nothing here creates a directory:
    resolution must be safe to run anywhere, including outside a project,
    where the answer is simply "no".
    """
    current = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isfile(os.path.join(current, "project.conf")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def store_dir(project: str) -> str:
    return os.path.join(project, STORE_DIRNAME)


def runs_dir(project: str) -> str:
    return os.path.join(store_dir(project), RUNS_DIRNAME)


RUN_SUBDIR = "run"
PLANE2_NAME = "plane2.json"


def list_snapshots(project: str) -> List[str]:
    """Every snapshot directory, oldest first.

    Sorted by name, which is the stamp, which is time order — no
    filesystem mtime is consulted, so a copied or restored store keeps
    its meaning.
    """
    root = runs_dir(project)
    if not os.path.isdir(root):
        return []
    return [
        os.path.join(root, name)
        for name in sorted(os.listdir(root))
        if os.path.isdir(os.path.join(root, name))
    ]


def has_run(snapshot: str) -> bool:
    return os.path.isdir(os.path.join(snapshot, RUN_SUBDIR))


def list_runs(project: str) -> List[str]:
    """The snapshots that hold an analyzable run directory, oldest first.

    Not the same list as `list_snapshots`, and the difference is the
    point: a capture whose build died before any element completed
    leaves a directory with the Plane 2 report in it and no `run/`, and
    treating that as `@prev` turns the next comparison into "baseline
    directory does not exist" — an error about a path the user never
    typed. Found exactly that way, by a snapshot that crashed mid-run.

    The incomplete directory is kept, because the half that survived is
    the expensive half. It simply is not what `@prev` means.
    """
    return [s for s in list_snapshots(project) if has_run(s)]


def is_alias(token: str) -> bool:
    return bool(_ALIAS.match(token or ""))


def resolve(token: str, start: Optional[str] = None) -> str:
    """Turn `@last` / `@prev` / `@<stamp-prefix>` into a run directory.

    Anything that is not an alias is returned untouched, so every command
    can route its positional through this without changing what an
    explicit path means.
    """
    if not is_alias(token):
        return token
    return os.path.join(resolve_snapshot(token, start), RUN_SUBDIR)


def resolve_plane2(token: str, start: Optional[str] = None) -> str:
    """The same alias, naming that snapshot's Plane 2 report (`UX-134`).

    Deliberately the *same* lookup as `resolve`: `@last` is one snapshot,
    and `bga correlate @last @last` must not pair one snapshot's run
    directory with another's report. The two functions differ only in
    which file inside the answer they name.
    """
    if not is_alias(token):
        return token
    snapshot = resolve_snapshot(token, start)
    plane2 = os.path.join(snapshot, PLANE2_NAME)
    if not os.path.isfile(plane2):
        raise StoreError(
            f"{token} resolves to {os.path.basename(snapshot)}, which has no "
            f"{PLANE2_NAME} - that capture recorded Plane 1 and not Plane 2. "
            f"Name a different snapshot, or pass the report's path."
        )
    return plane2


def sibling_plane2(run_dir: str) -> Optional[str]:
    """The Plane 2 report beside a run directory, if there is one.

    Read off the filesystem rather than off how the argument was spelled,
    so `@last` and the full path it resolves to behave identically -
    which is what makes this a fact about the capture rather than a
    reward for using the store.
    """
    if os.path.basename(os.path.normpath(run_dir)) != RUN_SUBDIR:
        return None
    plane2 = os.path.join(os.path.dirname(os.path.normpath(run_dir)), PLANE2_NAME)
    return plane2 if os.path.isfile(plane2) else None


def resolve_snapshot(token: str, start: Optional[str] = None) -> str:
    """The snapshot directory an alias names.

    Candidates are `list_runs`, not `list_snapshots`, for every artifact:
    an alias has to mean one snapshot whichever file is being asked for,
    and a capture with no run directory is not one `@last` ever meant
    (`UX-126`).
    """
    project = project_root(start)
    if project is None:
        raise StoreError(
            f"{token} is a snapshot alias, and there is no BuildStream project "
            f"here to resolve it against (no project.conf in this directory or "
            f"any parent). Run it from inside a project, or pass a path."
        )
    snapshots = list_runs(project)
    if not snapshots:
        incomplete = len(list_snapshots(project))
        raise StoreError(
            f"{token} names a snapshot and {project} has "
            + (f"{incomplete} whose build produced no run directory."
               if incomplete else "none yet.")
            + " `bga snapshot -- bst build TARGET` takes one."
        )

    name = token[1:]
    if name == "last":
        return snapshots[-1]
    if name == "prev":
        if len(snapshots) < 2:
            raise StoreError(
                f"@prev needs two snapshots and {project} has one. Take another "
                f"after your change and the comparison becomes automatic."
            )
        return snapshots[-2]

    matches = [s for s in snapshots if os.path.basename(s).startswith(name)]
    if not matches:
        raise StoreError(
            f"no snapshot in {project} starts with {name!r}. "
            f"Have: {', '.join(os.path.basename(s) for s in snapshots[-4:])}"
        )
    if len(matches) > 1:
        raise StoreError(
            f"{name!r} matches {len(matches)} snapshots: "
            f"{', '.join(os.path.basename(s) for s in matches)}"
        )
    return matches[0]


def new_snapshot_dir(project: str, now: Optional[datetime] = None) -> str:
    """Create and return the next snapshot directory.

    The name is the UTC stamp plus a short disambiguator, so two
    snapshots inside one second do not collide and the listing still
    sorts in time order.
    """
    stamp = (now or datetime.now(timezone.utc)).strftime(_STAMP)
    root = runs_dir(project)
    os.makedirs(root, exist_ok=True)
    _write_gitignore(project)
    for suffix in range(100):
        name = stamp if suffix == 0 else f"{stamp}-{suffix:02d}"
        path = os.path.join(root, name)
        if not os.path.exists(path):
            os.makedirs(path)
            return path
    raise StoreError(f"could not find an unused snapshot name under {root}")


def _write_gitignore(project: str) -> None:
    """`.bga/` ignores itself.

    Dropped rather than asked for: a store the user has to remember to
    gitignore is a store that ends up committed, and the run directories
    inside it are build artifacts by any definition.
    """
    path = os.path.join(store_dir(project), ".gitignore")
    if os.path.exists(path):
        return
    os.makedirs(store_dir(project), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            "# Written by `bga snapshot` (UX-126). Captures are build\n"
            "# artifacts: they are reproducible from the build and are\n"
            "# large. Delete entries under runs/ whenever you like.\n"
            "*\n"
        )


def read_config(project: str) -> dict:
    """The project's sticky capture flags, or `{}`.

    `UX-126` item 4: deciding `--trace-spine=auto --trace-opens` once per
    project rather than remembering it per invocation. Safe because every
    report already records what actually ran (`UX-95`/`UX-113`), so
    stickiness cannot make a capture *claim* something it did not do.
    """
    path = os.path.join(store_dir(project), CONFIG_NAME)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_config(project: str, config: dict) -> None:
    os.makedirs(store_dir(project), exist_ok=True)
    _write_gitignore(project)
    path = os.path.join(store_dir(project), CONFIG_NAME)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, sort_keys=True)
        handle.write("\n")


def store_size_bytes(project: str) -> int:
    total = 0
    for snapshot in list_snapshots(project):
        for root, _dirs, files in os.walk(snapshot):
            for name in files:
                try:
                    total += os.path.getsize(os.path.join(root, name))
                except OSError:
                    continue
    return total
