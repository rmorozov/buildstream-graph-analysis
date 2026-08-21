#!/usr/bin/env python3
"""UX-126: the loop, spelled as itself.

    bga snapshot -- bst build target.bst    # capture + extract + analyze
    # …edit…
    bga snapshot -- bst build target.bst    # and compare against @prev

What that replaces is three commands and five invented paths:

    bga capture run --wrapped-log /tmp/plane1.log --trace-opens \\
        /path/to/project /tmp/plane2.json -- bst build target.bst
    bga extract --format wrapped /path/to/project /tmp/plane1.log /tmp/run
    bga analyze /tmp/run --plane2 /tmp/plane2.json

`bga capture run` already holds everything the second and third commands
need — the project path, the wrapped log it just wrote, the Plane 2
report path. The split exists because the pieces shipped in different
rounds, not because a user benefits from it.

This *composes* those commands rather than reimplementing them: it calls
`bga capture run --run-dir`, then `bga analyze`, then `bga compare`,
through their own `main()`s. Nothing here can drift from what the
explicit three commands do, because it is them - including the UX-78
refusals, which a cross-mode pair still hits.
"""

HELP = """Capture, analyze, and compare against the previous run - one command.

Runs the build under the tracer, stores the capture in `.bga/runs/`, prints
the analysis, and compares it against the last healthy snapshot. Run it once
before your change and once after; the comparison is automatic.

Full background: docs/guides/local-loop.md
"""
import argparse
import json
import gzip
import os
import shutil
import sys
import time
from typing import List, Optional, Tuple

from bga import run_store

# What a snapshot is made of. Deliberately the layout the published
# capture refs already use (UX-81/UX-96), so nothing downstream learns a
# second shape.
RUN_SUBDIR = "run"
PLANE2_NAME = "plane2.json"
# UX-188: the raw Plane 2 log, gzipped, kept beside the processed
# report. `bga native-to-chrome combined` - the plane merge the field
# asked for - reads the *raw* log, and snapshots kept only the processed
# one, so the merge existed for captures nobody made by default.
#
# Default-on, because the measured cost is small: on two real captures a
# raw log gzips to **8.0%** and **8.6%** of itself (676,931 -> 53,828 B;
# 150,969 -> 12,915 B), which is 12% on top of the processed report it
# sits beside. `--no-keep-raw` turns it off.
RAW_LOG_NAME = "plane2.log.gz"
WRAPPED_LOG_NAME = "build.log"
CONTEXT_NAME = "capture-context.txt"


def _capture_context(project: str, command: List[str], config: dict) -> str:
    """What this capture was, in the terms UX-95 made the report carry.

    Written before the build rather than after, so a snapshot of a build
    that died still says what was attempted.
    """
    import platform

    return "\n".join([
        f"project={project}",
        f"command={' '.join(command)}",
        f"trace_opens={'true' if config.get('trace_opens', True) else 'false'}",
        f"trace_spine={config.get('trace_spine', 'auto')}",
        f"runner_os={platform.platform()}",
        f"nproc={os.cpu_count()}",
    ]) + "\n"


def take_snapshot(project: str, command: List[str], config: dict,
                  snapshot: Optional[str] = None, diagnose: bool = False,
                  no_inject: bool = False, inhibit: bool = False,
                  keep_raw: bool = True) -> Tuple[str, int]:
    """Capture into a new snapshot directory. Returns it and the build's
    own exit code - which is the build's answer, not the capture's."""
    from .bst_native_build_tracer import main as capture_main

    snapshot = snapshot or run_store.new_snapshot_dir(project)
    with open(os.path.join(snapshot, CONTEXT_NAME), "w", encoding="utf-8") as handle:
        handle.write(_capture_context(project, command, config))

    argv = ["run", "--wrapped-log", os.path.join(snapshot, WRAPPED_LOG_NAME),
            "--run-dir", os.path.join(snapshot, RUN_SUBDIR)]
    if keep_raw:
        # Written uncompressed by the capture, then compressed in place
        # below: the tracer streams into it for hours and gzip is the
        # copy-out step, not the write path.
        argv += ["--raw-log", os.path.join(snapshot, RAW_LOG_NAME[:-3])]
    if config.get("trace_opens", True):
        argv.append("--trace-opens")
    # `=` rather than a separate token: `--trace-spine` takes an optional
    # value, so `--trace-spine auto PROJECT` would be ambiguous with the
    # positional that follows it (UX-113's own capture command hit this).
    argv.append(f"--trace-spine={config.get('trace_spine', 'auto')}")
    # UX-146: deliberately not sticky. These are for one debugging
    # session, and a remembered `--no-inject` would silently stop
    # capturing anything.
    if diagnose:
        argv.append("--diagnose")
    if no_inject:
        argv.append("--no-inject")
    if inhibit:
        argv.append("--inhibit")
    argv += [project, os.path.join(snapshot, PLANE2_NAME), "--"] + list(command)

    print(f"Capturing into {snapshot}", file=sys.stderr)
    exit_code = capture_main(argv)
    if keep_raw:
        _compress_raw_log(snapshot)
    return snapshot, exit_code


def _compress_raw_log(snapshot: str) -> None:
    """gzip the raw Plane 2 log in place, best effort.

    Failing to compress must never lose the capture that just took three
    hours - so an error here leaves the uncompressed log where it is and
    says so, rather than raising.
    """
    plain = os.path.join(snapshot, RAW_LOG_NAME[:-3])
    if not os.path.exists(plain):
        return
    try:
        with open(plain, "rb") as source, gzip.open(
                os.path.join(snapshot, RAW_LOG_NAME), "wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
        os.remove(plain)
    except OSError as error:
        print(f"Warning: could not compress the raw Plane 2 log ({error}); "
              f"it is kept uncompressed at {plain}.", file=sys.stderr)


def _CompactRawHelp(prog):
    """UX-158: one shared compact help layout, imported lazily so
    this module stays runnable on its own."""
    from bga.help_format import CompactRawHelp
    return CompactRawHelp(prog)

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=HELP, formatter_class=_CompactRawHelp,
    )
    parser.add_argument(
        "--project", default=None,
        help='The project to snapshot.'
    )
    parser.add_argument(
        "--trace-opens", dest="trace_opens", action="store_true", default=None,
        help='Record opened paths (UX-46).'
    )
    parser.add_argument(
        "--no-trace-opens", dest="trace_opens", action="store_false",
        help="Turn opened-path recording off, and remember that.",
    )
    parser.add_argument(
        "--trace-spine", choices=["off", "on", "auto"], default=None,
        help='The ptrace spine\'s policy (UX-113).'
    )
    parser.add_argument(
        "--no-compare", action="store_true",
        help='Take the snapshot and report on it, but do not compare against the previous one.'
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List this project's snapshots, with sizes, and exit.",
    )
    parser.add_argument(
        "--format", choices=("text", "json"), default="text",
        help="`json` emits the listing as a `store/v1` document, which "
             "`bga view` draws the store trend from. Only with --list.",
    )
    # UX-159: the store had a size warning and no way to act on it.
    # A subcommand rather than a flag, because it deletes.
    parser.add_argument(
        "--prune", action="store_true",
        help="Delete old snapshots. Needs --keep and/or --older-than.",
    )
    parser.add_argument(
        "--keep", type=int, default=None, metavar="N",
        help="With --prune: keep the newest N snapshots.",
    )
    parser.add_argument(
        "--older-than", type=float, default=None, metavar="DAYS",
        help="With --prune: delete snapshots older than DAYS.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="With --prune: say what would go, delete nothing.",
    )
    parser.add_argument(
        "--diagnose", action="store_true",
        help='UX-146: record what the bwrap shim received and exec\'d, into the snapshot, and print a summary.'
    )
    parser.add_argument(
        "--no-inject", action="store_true",
        help='UX-146: run the build with the shim installed but injecting nothing, to find out whether the argv rewrite is what breaks it.'
    )
    parser.add_argument(
        "--no-keep-raw", action="store_true",
        help="UX-188: do not keep the raw Plane 2 log. It is kept gzipped by "
             "default (8%% of its size, measured) because `bga timeline` needs "
             "it to render Plane 2's lanes."
    )
    parser.add_argument(
        "--inhibit", action="store_true",
        help="UX-185: stop the machine sleeping while the build runs, via "
             "systemd-inhibit (and gnome-session-inhibit when present). Not "
             "the default - taking a lock on your power management uninvited "
             "is not bga's call. A suspend is detected either way."
    )
    parser.add_argument(
        "--no-progress", action="store_true",
        help="UX-183: no in-phase progress line, even on a terminal. Same "
             "as setting BGA_NO_PROGRESS=1."
    )
    parser.add_argument("cmd", nargs=argparse.REMAINDER,
                        help="The build to run, e.g. -- bst build all.bst.")
    args = parser.parse_args(argv)

    if args.no_progress:
        # UX-183: an environment variable rather than a threaded-through
        # flag, because the phases that draw progress are four modules
        # deep and none of them should learn about argv. `progress`
        # reads it fresh on every ticker.
        os.environ["BGA_NO_PROGRESS"] = "1"

    project = args.project or run_store.project_root()
    if project is None:
        print(
            "Error: no BuildStream project here (no project.conf in this "
            "directory or any parent). Run this from inside a project, or pass "
            "--project PATH.",
            file=sys.stderr,
        )
        return 2

    if args.list:
        return _list(project, as_json=args.format == "json")

    # `prune` is spelled as a bare word, because that is how it reads and
    # how the docs write it: `bga snapshot prune --keep 5`. Its own flags
    # have to be parsed here rather than by the main parser: `cmd` is
    # `argparse.REMAINDER`, so everything after the first positional is
    # swallowed verbatim - which is exactly what the wrapped build needs
    # and exactly what a subcommand does not.
    if args.prune or (args.cmd and args.cmd[0] == "prune"):
        rest = args.cmd[1:] if (args.cmd and args.cmd[0] == "prune") else []
        prune_parser = argparse.ArgumentParser(
            prog="bga snapshot prune", formatter_class=_CompactRawHelp,
            description="Delete old snapshots, never @last or @prev.")
        prune_parser.add_argument("--keep", type=int, default=args.keep,
                                  metavar="N", help="Keep the newest N.")
        prune_parser.add_argument("--older-than", type=float,
                                  default=args.older_than, metavar="DAYS",
                                  help="Delete snapshots older than DAYS.")
        prune_parser.add_argument("--dry-run", action="store_true",
                                  default=args.dry_run,
                                  help="Say what would go, delete nothing.")
        pruned = prune_parser.parse_args(rest)
        if pruned.keep is None and pruned.older_than is None:
            print("Error: prune needs --keep N and/or --older-than DAYS. "
                  "Nothing was deleted.", file=sys.stderr)
            return 2
        return _prune(project, pruned.keep, pruned.older_than, pruned.dry_run)

    command = [token for token in args.cmd if token != "--"]
    if not command:
        print("Error: nothing to run. Usage: bga snapshot -- bst build TARGET",
              file=sys.stderr)
        return 2

    config = _sticky_config(project, args)
    # `list_runs`, not `list_snapshots`: a capture whose build died
    # before any element completed has no run directory to compare
    # against, and offering it as `@prev` produces an error about a
    # path the user never typed.
    previous = run_store.list_runs(project)
    snapshot, build_exit = take_snapshot(project, command, config,
                                         diagnose=args.diagnose,
                                         no_inject=args.no_inject,
                                         inhibit=args.inhibit,
                                         keep_raw=not args.no_keep_raw)

    if args.no_inject:
        # Nothing was captured, so there is nothing to analyze and
        # certainly nothing to compare. Saying so beats an analysis of an
        # empty trace, which would read as a measurement.
        print(f"\n--no-inject: the build ran with the shim installed and "
              f"injecting nothing, so this snapshot holds no trace. The "
              f"build exited {build_exit}.\n"
              f"Diagnostics: {os.path.join(snapshot, PLANE2_NAME)}"
              f".diagnostics.jsonl", file=sys.stderr)
        return build_exit

    run_dir = os.path.join(snapshot, RUN_SUBDIR)
    if build_exit == 130:
        # UX-157: an interrupt is not a build failure and must not read
        # as one. The capture already salvaged and analyzed whatever
        # completed; what is left is to name the exit for what it was.
        print(f"\nInterrupted. The capture was kept in {snapshot}. Whatever "
              f"completed before the interrupt is in the report above, and a "
              f"comparison against this snapshot obeys the same incompleteness "
              f"rules as any unfinished build (UX-156).", file=sys.stderr)
    if not os.path.isdir(run_dir):
        # The capture kept whatever it got (the Plane 2 report is on
        # disk); there is simply nothing to analyze. Say which of the two
        # happened rather than printing an analyzer error.
        print(f"\nNo run directory was extracted - the build exited "
              f"{build_exit} and its log has no completed elements to read. "
              f"The Plane 2 capture is in {snapshot}.", file=sys.stderr)
        if not args.diagnose and not args.no_inject:
            # UX-147 item 5: the one thing worth saying to someone whose
            # build works under plain `bst` and not here.
            print("Re-run with --diagnose to record what the bwrap shim "
                  "received and exec'd; --no-inject then says whether the "
                  "rewrite is what breaks it.", file=sys.stderr)
        return build_exit or 1

    print()
    _analyze(run_dir, os.path.join(snapshot, PLANE2_NAME))

    if not args.no_compare and previous:
        print()
        baseline, skipped = _healthy_baseline(previous)
        if skipped:
            print(_walkback_notice(baseline, skipped))
        if baseline is not None:
            _compare(baseline, snapshot)
    elif not args.no_compare:
        print("\nThis is the first snapshot of this project - make your change "
              "and run the same command again, and the comparison against it "
              "is automatic.")

    _warn_if_large(project)
    # The build's own status is the answer, as everywhere else here: a
    # failed build must not look like a successful snapshot.
    return build_exit


def _sticky_config(project: str, args: argparse.Namespace) -> dict:
    """What was passed wins; what was not is what this project last used.

    A project with no config starts at the recommended setting rather
    than at nothing (UX-126 item 4). Safe because every report records
    what actually ran (UX-95/UX-113), so stickiness cannot make a capture
    *claim* something it did not do.
    """
    defaults = {"trace_opens": True, "trace_spine": "auto"}
    config = dict(defaults)
    stored = run_store.read_config(project)
    config.update(stored)
    if args.trace_opens is not None:
        config["trace_opens"] = args.trace_opens
    if args.trace_spine is not None:
        config["trace_spine"] = args.trace_spine
    run_store.write_config(project, config)

    # UX-145: say which remembered flags are in force. Set
    # `--trace-spine=off` once and three weeks later a bare
    # `bga snapshot` still runs spine-off; what ran *is* recorded in the
    # report, but recording a surprise is not preventing one, and the
    # blind spot is otherwise discovered at read time. Printed only when
    # the stored config actually changes something, so the ordinary case
    # stays quiet.
    remembered = {key: value for key, value in stored.items()
                  if key in defaults and value != defaults[key]
                  and getattr(args, key, None) is None}
    if remembered:
        flags = " ".join(
            ("--trace-opens" if config["trace_opens"] else "--no-trace-opens")
            if key == "trace_opens" else f"--trace-spine={config['trace_spine']}"
            for key in sorted(remembered))
        print(f"Using {os.path.join(run_store.store_dir(project), 'config')}: "
              f"{flags}", file=sys.stderr)
    return config


def _analyze(run_dir: str, plane2: str) -> int:
    from bga.cli import main as cli_main

    argv = ["analyze", run_dir]
    if os.path.isfile(plane2):
        argv += ["--plane2", plane2]
    return cli_main(argv)


def _snapshot_failed(snapshot: str) -> bool:
    """Is this snapshot's build incomplete - failed, or interrupted?

    Read straight out of `run-context.json`'s `build_outcome` (`UX-54`),
    not by analyzing the run: choosing a baseline must not cost a second
    full analysis of every snapshot in the store, and this is the same
    field the analyzer would consult.

    A snapshot that does not say is treated as healthy. `build_outcome`
    is written unconditionally, so its absence means the capture predates
    `UX-54` - and refusing to compare against every older run would be a
    worse failure than the one this prevents.
    """
    path = os.path.join(snapshot, RUN_SUBDIR, "run-context.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            outcome = json.load(handle).get("build_outcome") or {}
    except (OSError, ValueError):
        return False
    # UX-157: interrupted counts too. Both mean "elements that never ran
    # contributed no time", which is the only property the baseline
    # choice cares about.
    return bool(outcome.get("failed_elements") or outcome.get("interrupted"))


def _healthy_baseline(previous):
    """The most recent snapshot whose build finished, and what was passed.

    `UX-156` item 3. `@prev` keeps its filed meaning - the previous
    snapshot, whatever it is - because that is an alias the user types
    and it must not silently mean something else. What changes is the
    baseline *snapshot* picks on its own, where round 16 measured the
    real damage: a failed run became `@prev`, and the next healthy
    snapshot was compared against wreckage at confidence 0.57 with
    nothing saying so.
    """
    skipped = []
    for candidate in reversed(previous):
        if _snapshot_failed(candidate):
            skipped.append(candidate)
            continue
        return candidate, list(reversed(skipped))
    return None, list(reversed(skipped))


def _walkback_notice(baseline: Optional[str], skipped: List[str]) -> str:
    """What the walk-back says it did, and why.

    `UX-164` item 2: the sentence was built for a plural list and read
    broken for the common single-skip case. `UX-176`: extracted from
    `main` so a guard can render both shapes instead of asserting that
    both wordings appear in the source - which they do whichever branch
    is reachable.
    """
    names = ", ".join(os.path.basename(p.rstrip("/")) for p in skipped)
    one = len(skipped) == 1
    if baseline is None:
        return (f"No comparison: the {len(skipped)} previous "
                f"snapshot{'' if one else 's'} ({names}) "
                f"{'records a build' if one else 'all record builds'} that "
                f"did not finish, and a duration delta against one is not a "
                f"measurement (UX-156). `bga compare` on an explicit pair "
                f"still works.")
    return (f"Comparing against {os.path.basename(baseline.rstrip('/'))} "
            f"rather than the previous snapshot: {names} "
            f"{'records a build' if one else 'record builds'} that did "
            f"not finish (UX-156).")


def _compare_refs(baseline_snapshot: str, candidate_snapshot: str) -> str:
    """The aliases that name *this* pair, or the stamps that do.

    `UX-164` item 1. This printed `@prev @last` unconditionally - and
    after a `UX-156` walk-back, `@prev` resolves to the snapshot that was
    *skipped* (it has a `run/`, so `list_runs` includes it). Pasting the
    suggested command reproduced exactly the wreckage comparison the
    walk-back exists to prevent, and got a refusal instead of the
    comparison printed above it.

    On a long-running project failed and interrupted runs are the store's
    common tenants, so the hint was wrong more often than right precisely
    where `UX-156` matters most.
    """
    project = run_store.project_root(baseline_snapshot) or \
        os.path.dirname(os.path.dirname(os.path.dirname(baseline_snapshot)))
    runs = run_store.list_runs(project)
    aliases = {}
    if runs:
        aliases[os.path.abspath(runs[-1])] = "@last"
    if len(runs) > 1:
        aliases[os.path.abspath(runs[-2])] = "@prev"

    def ref(snapshot: str) -> str:
        alias = aliases.get(os.path.abspath(snapshot))
        # The stamp-prefix grammar already exists, so a snapshot with no
        # alias still has a short name the user can type.
        return alias or "@" + os.path.basename(snapshot.rstrip("/"))

    return f"{ref(baseline_snapshot)} {ref(candidate_snapshot)}"


def _compare(baseline_snapshot: str, candidate_snapshot: str) -> int:
    """The loop's whole point, and the reason the store exists.

    Through `bga compare` itself, so UX-78's refusals apply unchanged: a
    cross-mode pair says so rather than comparing. Both Plane 2 reports
    are passed because the store has them - joining yesterday's report to
    today's run is precisely the mistake this item exists to remove, and
    the store is the only place that knows which is which.
    """
    from bga.cli import main as cli_main

    argv = ["compare", os.path.join(baseline_snapshot, RUN_SUBDIR),
            os.path.join(candidate_snapshot, RUN_SUBDIR)]
    for flag, snapshot in (("--baseline-plane2", baseline_snapshot),
                           ("--candidate-plane2", candidate_snapshot)):
        plane2 = os.path.join(snapshot, PLANE2_NAME)
        if os.path.isfile(plane2):
            argv += [flag, plane2]
    print(f"$ bga compare {_compare_refs(baseline_snapshot, candidate_snapshot)}"
          f"   # {' '.join(argv[1:3])}")
    return cli_main(argv)


def store_listing(project: str) -> dict:
    """The store as data - one `store/v1` document.

    `UX-196`: the text listing and `--format json` are rendered from
    *this*, so the viewer's store trend and `--list` cannot disagree
    about what is on disk. Incomplete captures are listed rather than
    hidden - they occupy the disk the size warning is about - but they
    carry no alias, because they are not what `@last` resolves to.
    """
    from bga import schemas

    snapshots = run_store.list_snapshots(project)
    runs = run_store.list_runs(project)
    aliases = {}
    if runs:
        aliases[runs[-1]] = "@last"
    if len(runs) > 1:
        aliases[runs[-2]] = "@prev"

    rows = []
    for path in snapshots:
        has_run = run_store.has_run(path)
        measured = _run_measurements(path) if has_run else {}
        rows.append({
            "stamp": os.path.basename(path),
            "path": os.path.abspath(path),
            "bytes": run_store.snapshot_size_bytes(path),
            "alias": aliases.get(path),
            "has_run": has_run,
            # UX-156/157/185's three ways to be incomplete, so the trend
            # can mark them rather than drawing them as measurements.
            "incomplete_reason": _incomplete_reason(path) if has_run else None,
            # UX-203: what the trend was always supposed to plot. The
            # view drew `bytes` - so "is this project drifting" was
            # answered by disk usage, which is not the question. Read
            # straight off run-context rather than analysed, because
            # this runs for every snapshot on every `bga view`.
            "total_duration_us": measured.get("total_duration_us"),
            "cache_hit_rate": measured.get("cache_hit_rate"),
        })
    _mark_verdicts(rows)
    return schemas.stamp({
        "project": os.path.abspath(project),
        "snapshots": rows,
        "count": len(rows),
        # Sum of file sizes, so it is a little under `du` (which also
        # counts directory entries) and matches `du --apparent-size`.
        "total_bytes": sum(row["bytes"] for row in rows),
    }, schemas.STORE)



def _run_measurements(snapshot: str) -> dict:
    """Duration and cache hit rate for one snapshot, cheaply.

    `UX-203`. Both come out of `run-context.json`, which is one small
    read: `wall_clock` carries the horizon, and `queue_summary`'s build
    queue carries what BuildStream skipped - a skipped build is a cache
    hit, which is the same thing `bga analyze` reports and the only
    cache signal a capture records without Plane 3.

    Everything is optional: a capture from before a field existed
    yields `None`, and the trend draws a gap rather than a zero.
    """
    path = os.path.join(snapshot, run_store.RUN_SUBDIR, "run-context.json")
    try:
        with open(path, encoding="utf-8") as handle:
            context = json.load(handle)
    except (OSError, ValueError):
        return {}

    out = {}
    clock = context.get("wall_clock") or {}
    start, end = clock.get("start_us"), clock.get("end_us")
    if isinstance(start, int) and isinstance(end, int) and end >= start:
        out["total_duration_us"] = end - start

    build = (context.get("queue_summary") or {}).get("build") or {}
    processed, skipped = build.get("processed"), build.get("skipped")
    if isinstance(processed, int) and isinstance(skipped, int):
        total = processed + skipped
        if total:
            out["cache_hit_rate"] = skipped / total
    return out


def _mark_verdicts(rows: List[dict]) -> None:
    """Give each row a `verdict_kind` against the runs before it.

    `UX-203` asked for "the verdict vs its walk-back baseline". Derived
    from the same `compute_band` the comparison uses, over the
    durations already collected - so it costs no analyses, and the
    trend's colouring cannot disagree with what `bga compare` would
    say about the same pair.

    `None` below `MIN_BASELINE_RUNS`, where there is no band to judge
    against, and for any run that is not a measurement at all.
    """
    from bga.compare import compute_band

    history: List[int] = []
    for row in rows:
        duration = row.get("total_duration_us")
        if duration is None or row.get("incomplete_reason"):
            row["verdict_kind"] = None
            continue
        band = compute_band(history) if history else None
        if band is None:
            row["verdict_kind"] = None
        elif duration > band["high_us"]:
            row["verdict_kind"] = "regressed"
        elif duration < band["low_us"]:
            row["verdict_kind"] = "improved"
        else:
            row["verdict_kind"] = "within_band"
        history.append(duration)


def _incomplete_reason(snapshot: str):
    """Why this snapshot is not a measurement, or None.

    Read straight off the run context rather than recomputed, so the
    one accessor `UX-185` consolidated stays the only answer.

    The first version passed the *run directory* to `load_run_context`,
    which takes the run-context **file** - and caught bare `Exception`,
    so every row came back `None` and the listing quietly said no
    snapshot was ever incomplete. Both halves are fixed: the path is
    right, and the catch names the three failures a listing should
    survive (an unreadable file, a malformed one, an older schema)
    rather than hiding a typo.
    """
    from bga.exceptions import IngestionError
    from bga.ingest.loader import load_run_context

    context = os.path.join(snapshot, run_store.RUN_SUBDIR, "run-context.json")
    try:
        return load_run_context(context).incomplete_reason
    except (OSError, IngestionError, json.JSONDecodeError, KeyError):
        return None


def _list(project: str, as_json: bool = False) -> int:
    """Everything on disk, with the aliases resolution would give it."""
    listing = store_listing(project)
    if as_json:
        print(json.dumps(listing, indent=2))
        return 0

    if not listing["snapshots"]:
        print(f"No snapshots in {project}. "
              f"`bga snapshot -- bst build TARGET` takes one.")
        return 0
    print(f"{listing['count']} snapshot(s) in {project}:")
    for row in listing["snapshots"]:
        if not row["has_run"]:
            suffix = "  (no run directory - the build produced no elements)"
        elif row["alias"]:
            suffix = f"  {row['alias']}"
        else:
            suffix = ""
        if row["incomplete_reason"]:
            suffix += f"  ({row['incomplete_reason']})"
        # UX-159: the size belongs next to the name. Without it the user
        # is told the store is large and left to guess which snapshot is
        # the heavy one.
        print(f"  {row['stamp']:<18}"
              f"{run_store.human_bytes(row['bytes']):>9}{suffix}")
    print(f"  {'total':<18}"
          f"{run_store.human_bytes(listing['total_bytes']):>9}")
    return 0


def _protected(project: str) -> set:
    """Snapshots `prune` must never delete.

    `@last` and `@prev` because they are what the next `bga compare`
    resolves to - and, `UX-167`, **the newest healthy run**, because that
    is what `UX-156`'s walk-back will choose as the next comparison's
    baseline.

    Round 17 hit the contradiction live: in a store whose two newest
    run-bearing snapshots were a failed run and an interrupted one,
    `prune --keep 2` protected exactly those two and offered to delete
    the store's only healthy snapshot. The two features were arguing -
    the walk-back saying "the newest runs are not measurements", prune
    saying "the newest runs are the ones worth keeping". The walk-back
    is right about which one the next comparison needs.

    The extra directory is only kept when the aliased two are unhealthy,
    so a store of healthy runs prunes exactly as before.

    The `baseline` config key that used to be read here is gone: nothing
    in production ever wrote it, so it guarded a phantom (`UX-167`).
    Protecting the walk-back's actual target covers what it was for.
    """
    runs = run_store.list_runs(project)
    keep = set(runs[-2:])
    if all(_snapshot_failed(run) for run in runs[-2:]):
        healthy, _skipped = _healthy_baseline(runs)
        if healthy:
            keep.add(healthy)
    return keep


def _prune(project: str, keep: Optional[int], older_than: Optional[float],
           dry_run: bool) -> int:
    """Delete snapshots by age or count, never the ones still referred to.

    `UX-159` item 3. The store had exactly one management affordance - a
    note at 2 GB advising hand-deletion - and no command that deletes
    anything.
    """
    snapshots = run_store.list_snapshots(project)
    if not snapshots:
        print(f"No snapshots in {project}.")
        return 0
    protected = _protected(project)

    # UX-167: a snapshot with no run directory - an interrupted capture
    # from before UX-157, or a `--no-inject` session - is not in
    # `list_runs`, not aliased, and not useful to anything. `--keep 2`
    # used to leave those standing while deleting run-bearing snapshots,
    # which is the store keeping exactly the wrong things.
    husks = [s for s in snapshots if not run_store.has_run(s)]
    live = [s for s in snapshots if s not in set(husks)]

    doomed = list(husks)
    if keep is not None:
        doomed.extend(live[:-keep] if keep > 0 else list(live))
    if older_than is not None:
        cutoff = time.time() - older_than * 86400
        doomed.extend(s for s in live if os.path.getmtime(s) < cutoff)
    doomed = [s for s in dict.fromkeys(doomed) if s not in protected]

    skipped = [s for s in snapshots if s in protected]
    if not doomed:
        print(f"Nothing to prune: {len(snapshots)} snapshot(s), "
              f"{len(skipped)} of them still referred to by @last/@prev.")
        return 0

    freed = 0
    husk_count = sum(1 for path in doomed if path in set(husks))
    for path in doomed:
        size = run_store.snapshot_size_bytes(path)
        freed += size
        print(f"{'would delete' if dry_run else 'deleted'} "
              f"{os.path.basename(path)}  {run_store.human_bytes(size)}")
        if not dry_run:
            shutil.rmtree(path, ignore_errors=True)
    print(f"{'would free' if dry_run else 'freed'} "
          f"{run_store.human_bytes(freed)} from {run_store.runs_dir(project)}")
    if husk_count:
        # Counted separately because they are a different thing: not old
        # captures, but captures that never produced anything.
        print(f"  ({husk_count} of those held no run directory)")
    if skipped:
        names = ", ".join(os.path.basename(s) for s in skipped)
        print(f"kept {names} - @last/@prev, which the next comparison needs")
    return 0


# Past this, the store is worth a word rather than a policy: the user
# deletes what they do not want, and a size warning is enough (UX-126's
# Out of Scope says so explicitly).
_SIZE_WARN_BYTES = 2 * 1024 * 1024 * 1024


def _warn_if_large(project: str) -> None:
    size = run_store.store_size_bytes(project)
    if size >= _SIZE_WARN_BYTES:
        print(
            f"\nNote: {run_store.runs_dir(project)} holds "
            f"{size / 1024 ** 3:.1f} GB. `bga snapshot prune --keep 5` "
            f"deletes all but the newest five, and never @last or @prev.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    sys.exit(main())
