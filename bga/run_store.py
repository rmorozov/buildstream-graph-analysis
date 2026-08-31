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

from . import progress

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

# UX-296: the two capacity scalars, written beside the Plane 2 report by
# the capture that already had them in hand. The store aggregate used to
# reach them by parsing every snapshot's whole `plane2.json` on every
# view of any run - measured 1.17 GB of RSS to view a 2 MB neighbour.
# Nothing on a read path may open the big file for them again.
RESOURCE_NAME = "plane2-resource.json"

# UX-296: the analysis this snapshot published, written by the capture
# that already ran it. `bga view` renders this rather than re-deriving
# it - re-deriving means parsing the Plane 2 monolith again, which on
# the field capture is 4.3 GB and thirty seconds before the socket even
# exists.
ANALYSIS_NAME = "analyze.json"

# `UX-378`: the host's own memory while the build ran, sampled by the
# capture. Beside the Plane 2 report rather than inside it, because it
# is a series in its own clock rather than a per-element reduction - and
# because an interrupted capture keeps the samples it took, which a key
# inside a report written at the end would not.
HOST_SAMPLES_NAME = "host-samples.jsonl"

# UX-155: bga's own scratch — the shim it puts on `$PATH`, the compiled
# hook and spine, and the unnamed intermediate logs. Project-local for
# the same reason the runs are: `TMPDIR` is inherited by every service
# `bst` starts, so using it to solve a problem that belongs to one
# directory bga owns reconfigures `buildbox-casd` and the sandbox too.
SCRATCH_DIRNAME = "tmp"


def scratch_dir(project: str) -> str:
    """Where bga puts files it will delete again. A path, not a mkdir —
    resolution stays safe to call anywhere, as everything else here is.
    """
    return os.path.join(store_dir(project), SCRATCH_DIRNAME)


def ensure_store_ignored(project: str) -> None:
    """Make sure a `.bga/` that exists ignores itself.

    A capture that never takes a snapshot still creates `.bga/tmp`, and
    without this it would leave the first untracked `.bga/` in the
    user's project with no `.gitignore` beside it — which is the thing
    `_write_gitignore` exists to prevent.
    """
    _write_gitignore(project)


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


def read_resource_profile(snapshot: str) -> dict:
    """The capacity scalars a capture recorded beside its report.

    `UX-296`. One small read, the shape `read_element_slice` already
    uses: the store is built on every `bga view`, for every snapshot, so
    anything a row needs has to be a file the size of the answer.

    `{}` for a capture written before this existed - which is a
    different claim from "this run had no Plane 2", and the aggregate
    says which by naming the command that would produce it.
    """
    import json

    try:
        with open(os.path.join(snapshot, RESOURCE_NAME),
                  encoding="utf-8") as handle:
            profile = json.load(handle)
    except (OSError, ValueError):
        return {}
    return profile if isinstance(profile, dict) else {}


def write_resource_profile(destination: str, native_report: dict) -> dict:
    """Record those scalars beside a Plane 2 report just written.

    Takes the report **in memory** - the caller has it because it just
    built it - so this costs one small write and no parse at all.
    """
    import json

    from .correlate import resource_profile

    profile = resource_profile(native_report or {})
    if not profile:
        return {}
    try:
        with open(destination, "w", encoding="utf-8") as handle:
            json.dump(profile, handle, indent=2, sort_keys=True)
    except OSError:
        # A sidecar is a convenience on top of a capture that already
        # succeeded, the same rule `write_element_slice` follows.
        return {}
    return profile


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


# UX-329: the raw trace log the timeline is rendered from, named here
# beside the report it belongs with. `tools/bga_snapshot.py` writes it;
# the absence grammar in `bga/plane2.py` has to be able to ask whether
# it is there without importing the capture.
RAW_LOG_NAME = "plane2.log.gz"


def sibling_raw_log(run_dir: str) -> Optional[str]:
    """The raw Plane 2 log beside a run directory, if there is one.

    The same filesystem question `sibling_plane2` asks, about the other
    half: the *report* is what the analysis reads and the *log* is what
    `bga timeline` renders, and a capture can have either without the
    other - which is the distinction `UX-329` exists to state.
    """
    if os.path.basename(os.path.normpath(run_dir)) != RUN_SUBDIR:
        return None
    snapshot = os.path.dirname(os.path.normpath(run_dir))
    for name in (RAW_LOG_NAME, RAW_LOG_NAME[:-3]):
        path = os.path.join(snapshot, name)
        if os.path.isfile(path):
            return path
    return None


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
        # UX-324: name them. `bga snapshot --list` shows these rows, and
        # a refusal that only counts them reads as a disagreement about
        # what is on disk.
        incomplete = [os.path.basename(s) for s in list_snapshots(project)]
        raise StoreError(
            f"{token} names a snapshot and {project} has "
            + (f"{len(incomplete)} whose build produced no run directory "
               f"({', '.join(incomplete[-4:])}) - `bga snapshot --list` "
               f"shows them."
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

    # UX-177 item 1: an exact name wins before prefix matching. The
    # store's own same-second disambiguation (`<stamp>`, `<stamp>-01`)
    # makes a full stamp a strict prefix of its sibling, so the walk-back
    # hint could print `@20260820T153932Z` and pasting it back raised
    # "matches 2 snapshots" - a hint the tool produced and then refused.
    exact = [s for s in snapshots if os.path.basename(s) == name]
    if exact:
        return exact[0]

    matches = [s for s in snapshots if os.path.basename(s).startswith(name)]
    if not matches:
        # UX-324: a prefix that names a directory `--list` shows must not
        # be told it does not exist. The candidate list here is
        # `list_runs` - deliberately, because an alias resolves only to a
        # capture that produced one - and the difference between the two
        # lists is exactly what the reader is looking at.
        debris = [os.path.basename(s) for s in list_snapshots(project)
                  if os.path.basename(s).startswith(name)]
        if debris:
            raise StoreError(
                f"{name!r} names {len(debris)} snapshot(s) in {project} with "
                f"no run directory ({', '.join(debris[-4:])}). "
                f"`bga snapshot --list` shows them and says why; an alias "
                f"resolves only to a capture that produced a run. "
                f"Resolvable: {', '.join(os.path.basename(s) for s in snapshots[-4:])}"
            )
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


SIZE_CACHE_NAME = ".size"


def _tree_signature(snapshot: str) -> tuple:
    """A cheap fingerprint of a snapshot's shape: (directory count, newest
    directory mtime).

    Every file added, removed or renamed anywhere in the tree bumps its
    parent directory's mtime, so this catches the changes that can move
    a *finished* snapshot's size without stat-ing one file. It costs one
    stat per directory instead of one per file - measured on a 50k-file,
    10-snapshot store: 0.025s against 0.19s for the sizing walk.
    """
    count = 0
    latest = 0
    for root, _dirs, _files in os.walk(snapshot):
        count += 1
        try:
            mtime = os.stat(root).st_mtime_ns
        except OSError:
            continue
        if mtime > latest:
            latest = mtime
    return count, latest


def snapshot_size_bytes(snapshot: str, use_cache: bool = True) -> int:
    """Bytes on disk under one snapshot directory.

    `UX-159`. Split out of `store_size_bytes` so `--list` can show which
    snapshot is the 1.8 GB one - the size warning could say the store
    was large, and the listing could not say where the weight sat, so
    the user was told to delete something by hand without being told
    which.

    `UX-168`: the answer is memoised in `<snapshot>/.size`, because
    nothing in bga writes into a snapshot after its capture finishes and
    both `--list` and the end-of-run size warning walk the whole store
    every time. Measured on a 50k-file store: 0.89s cold, 0.19s warm,
    per invocation. The memo is keyed on `_tree_signature`, so it is
    dropped if anything in the tree moved; a store on read-only media
    simply never writes one and pays the walk.
    """
    signature = _tree_signature(snapshot) if use_cache else None
    if use_cache:
        cached = _read_size_cache(snapshot, signature)
        if cached is not None:
            return cached
    total = 0
    # UX-183: the cold walk is 0.89s on a 50k-file store and grows with
    # the store; on the machine that just finished a three-hour build it
    # is the last thing between the user and their report.
    tick = progress.ticker("measuring the store")
    for root, _dirs, files in os.walk(snapshot):
        tick.step()
        for name in files:
            if root == snapshot and name == SIZE_CACHE_NAME:
                # The memo is bga's own bookkeeping, not capture output;
                # counting it would make the number depend on whether it
                # had been asked for before.
                continue
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
    tick.done()
    if use_cache:
        _write_size_cache(snapshot, total)
    return total


def _read_size_cache(snapshot: str, signature: tuple) -> Optional[int]:
    try:
        with open(os.path.join(snapshot, SIZE_CACHE_NAME), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("dirs") != signature[0] or data.get("mtime_ns") != signature[1]:
        return None
    size = data.get("bytes")
    return size if isinstance(size, int) else None


def _write_size_cache(snapshot: str, total: int) -> None:
    path = os.path.join(snapshot, SIZE_CACHE_NAME)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"bytes": total}, handle)
        # The signature is taken *after* the file exists, so the write
        # that creates it does not immediately invalidate what it says.
        count, latest = _tree_signature(snapshot)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"bytes": total, "dirs": count, "mtime_ns": latest}, handle)
    except OSError:
        # A read-only or full store still reports sizes; it just pays
        # the walk every time.
        return


def store_size_bytes(project: str) -> int:
    return sum(snapshot_size_bytes(s) for s in list_snapshots(project))


def human_bytes(size: int) -> str:
    """`du -h`-style, because that is what the user will compare against."""
    for unit in ("B", "K", "M", "G", "T"):
        if size < 1024 or unit == "T":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}T"


# `UX-381`: the capture directory as a stated contract.
#
# Every published `bga` command line names a path inside `.bga/`, and
# the tool prints them itself at the end of every capture. `@last` and
# `@prev` resolve by listing `runs/`; `bga view` reads `run/`; `bga
# correlate` finds `plane2.json` as a sibling; `bga timeline` reads
# `plane2.log.gz`; the aggregator walks the lot. The layout is
# load-bearing in a dozen places and, until this, was written down in
# none: Part 32's registry named one of fifteen paths, and the only
# file-layout table in the documentation described a *different*
# directory - the CI field-capture bundle, with different names for the
# same two files.
#
# This is `UX-328`'s rule one level up. Every document `bga` emits
# answers for its own schema; the directory those documents live in -
# which is the thing users paste into issues, tar up, and hand to CI -
# answered for nothing.
#
# The constants above are the values; this is the statement. Each row
# says what writes a path, what reads it, which contract it carries
# where it has one, and - the part a reader could previously only learn
# from an error - whether it is required and what its absence means.
SCHEMA = "capture-layout/v1"

# And the one contract inside this directory that no `bga` module
# stamps: `host-samples/v1` is written by
# `tools/bst_native_build_tracer.py`, and `bga.contracts` walks the
# `bga` package only - so without this the id is written to every
# sampled capture and inventoried nowhere, which is `UX-248`'s defect
# one directory over. The module that knows the directory names it.
OWNED = ("host-samples/v1",)

# Presence, as three words rather than a boolean, because "not there"
# has three different meanings in this directory and a consumer that
# cannot tell them apart cannot tell a broken capture from a cheap one.
REQUIRED = "required"          # absent means the capture is unusable
CONDITIONAL = "conditional"    # absent means that option was off
DERIVED = "derived"            # absent means nothing; it is rebuilt on demand

CAPTURE_LAYOUT = (
    # (path relative to the project, presence, contract, what it is)
    (f"{STORE_DIRNAME}/", REQUIRED, None,
     "the project-local store `UX-126` introduced. Everything below is "
     "relative to it; `bga` creates it on the first capture."),
    (f"{STORE_DIRNAME}/.gitignore", DERIVED, None,
     "written once so a clone does not ship the capture archive "
     "(`UX-189`). Absent only in a store made before that item; the "
     "next capture writes it."),
    (f"{STORE_DIRNAME}/{CONFIG_NAME}", CONDITIONAL, None,
     "the store's own settings, written when one is set. Absent means "
     "every setting is at its default."),
    (f"{STORE_DIRNAME}/{SCRATCH_DIRNAME}/", DERIVED, None,
     "`bga`'s scratch: the `$PATH` shim, the compiled hook and spine, "
     "and unnamed intermediates (`UX-155`). Never read across "
     "captures; safe to delete."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/", REQUIRED, None,
     "one directory per capture, named by UTC stamp. `@last` and "
     "`@prev` resolve by listing it, so its ordering is part of the "
     "contract: the names sort chronologically as strings."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/", REQUIRED, None,
     "one capture: the snapshot `bga snapshot --list` enumerates and "
     "`@last` names. The stamp is UTC and sorts chronologically as a "
     "string, which is what makes the listing an ordering."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/{RUN_SUBDIR}/", REQUIRED, None,
     "the run directory - the unit every published command line takes "
     "a path to. Absent on a build that failed before any element "
     "completed (`UX-156`), which is a capture with nothing to "
     "analyse rather than a corrupt one."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/{RUN_SUBDIR}/graph.json", REQUIRED, "graph/v9",
     "the declared element graph, from `bst show`."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/{RUN_SUBDIR}/trace.json", REQUIRED, "trace/v9",
     "the scheduler's own spans and phases - Plane 1."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/{RUN_SUBDIR}/run-context.json", REQUIRED,
     "run-context/v9",
     "what the run was: identity, host manifest (`host/v2` inside it), "
     "scheduler configuration, and the resolved `native_max_jobs` "
     "(`UX-377`)."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/{RUN_SUBDIR}/chrome_trace.json", DERIVED,
     None,
     "the Plane 1 trace in the legacy Chrome JSON shape. Present only "
     "on a capture taken before `UX-452`: the extraction wrote it for "
     "a person to drag into perfetto.dev, `UX-437`'s census measured "
     "that no reader opens it, and `bga timeline --format chrome` "
     "renders the same shape on demand from `trace.json`. Safe to "
     "delete; nothing rewrites it."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/{RUN_SUBDIR}/sources.json", CONDITIONAL,
     "sources/v1",
     "the source inventory (`UX-171`), read by `bga blast`. Absent "
     "means the capture could not resolve the project's sources, and "
     "`blast` says so rather than reporting an empty inventory."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/{PLANE2_NAME}", CONDITIONAL, "plane2/v3",
     "the Plane 2 report - what ran inside the sandboxes. Absent on a "
     "capture taken without Plane 2, and every Plane 2 section of "
     "every output is then absent rather than empty."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/{RAW_LOG_NAME}", CONDITIONAL, None,
     "the raw per-process trace the report was folded from, gzipped. "
     "`bga timeline` renders from this; absent means no timeline, "
     "which is a different absence from no report (`UX-329`)."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/{RESOURCE_NAME}", CONDITIONAL, None,
     "the two capacity scalars, beside the report so the aggregator "
     "never opens the big file for them (`UX-296`). Absent where the "
     "report is."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/{HOST_SAMPLES_NAME}", CONDITIONAL,
     "host-samples/v1",
     "the host's memory and swap while the build ran, one JSON object "
     "per line (`UX-378`). Absent on a capture taken before that item "
     "or with sampling unavailable."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/{ANALYSIS_NAME}", CONDITIONAL, "analyze/v4",
     "the analysis this capture published, so `bga view` renders "
     "rather than re-deriving (`UX-296`). Absent means the viewer "
     "parses the run itself, and the trace carries no graph structure "
     "(`UX-380`)."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/build.log", CONDITIONAL, None,
     "the wrapped BuildStream log, kept because its first line records "
     "the real invocation (`UX-29`). `bga timeline` needs it and "
     "refuses without it."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/element-slice.json", CONDITIONAL, None,
     "which elements the capture was asked for, where it was asked "
     "for a slice rather than the whole project."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/capture-context.txt", CONDITIONAL, None,
     "what the capture did and why, in prose - the diagnostics "
     "`UX-146` writes. Never parsed."),
    (f"{STORE_DIRNAME}/{RUNS_DIRNAME}/<stamp>/{SIZE_CACHE_NAME}", DERIVED, None,
     "a cached size for this snapshot, so `--list` does not walk every "
     "run. Rebuilt when the tree signature changes; safe to delete."),
)


def layout_paths() -> List[str]:
    """Every path the capture directory contract names."""
    return [path for path, _presence, _contract, _what in CAPTURE_LAYOUT]


def layout_presence(path: str) -> Optional[str]:
    """`REQUIRED`, `CONDITIONAL`, `DERIVED` - or `None` for a path the
    contract does not name, which is the answer a guard is looking for.
    """
    for named, presence, _contract, _what in CAPTURE_LAYOUT:
        if named == path:
            return presence
    return None
