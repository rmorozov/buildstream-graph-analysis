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
import argparse
import os
import sys
from typing import List, Optional, Tuple

from bga import run_store

# What a snapshot is made of. Deliberately the layout the published
# capture refs already use (UX-81/UX-96), so nothing downstream learns a
# second shape.
RUN_SUBDIR = "run"
PLANE2_NAME = "plane2.json"
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
                  no_inject: bool = False) -> Tuple[str, int]:
    """Capture into a new snapshot directory. Returns it and the build's
    own exit code - which is the build's answer, not the capture's."""
    from .bst_native_build_tracer import main as capture_main

    snapshot = snapshot or run_store.new_snapshot_dir(project)
    with open(os.path.join(snapshot, CONTEXT_NAME), "w", encoding="utf-8") as handle:
        handle.write(_capture_context(project, command, config))

    argv = ["run", "--wrapped-log", os.path.join(snapshot, WRAPPED_LOG_NAME),
            "--run-dir", os.path.join(snapshot, RUN_SUBDIR)]
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
    argv += [project, os.path.join(snapshot, PLANE2_NAME), "--"] + list(command)

    print(f"Capturing into {snapshot}", file=sys.stderr)
    return snapshot, capture_main(argv)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--project", default=None,
        help="The project to snapshot. Default: the nearest enclosing one, "
             "found by walking up for project.conf.",
    )
    parser.add_argument(
        "--trace-opens", dest="trace_opens", action="store_true", default=None,
        help="Record opened paths (UX-46). Sticky: stored in .bga/config and "
             "reused until changed.",
    )
    parser.add_argument(
        "--no-trace-opens", dest="trace_opens", action="store_false",
        help="Turn opened-path recording off, and remember that.",
    )
    parser.add_argument(
        "--trace-spine", choices=["off", "on", "auto"], default=None,
        help="The ptrace spine's policy (UX-113). Sticky, like --trace-opens. "
             "Default for a new project: auto.",
    )
    parser.add_argument(
        "--no-compare", action="store_true",
        help="Take the snapshot and report on it, but do not compare against "
             "the previous one.",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List this project's snapshots and exit.",
    )
    parser.add_argument(
        "--diagnose", action="store_true",
        help="UX-146: record what the bwrap shim received and exec'd, into "
             "the snapshot, and print a summary. For when a capture fails on "
             "a build that plain `bst` completes. Not sticky.",
    )
    parser.add_argument(
        "--no-inject", action="store_true",
        help="UX-146: run the build with the shim installed but injecting "
             "nothing, to find out whether the argv rewrite is what breaks it. "
             "Captures nothing. Implies --diagnose. Not sticky.",
    )
    parser.add_argument("cmd", nargs=argparse.REMAINDER,
                        help="The build to run, e.g. -- bst build all.bst")
    args = parser.parse_args(argv)

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
        return _list(project)

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
                                         no_inject=args.no_inject)

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
        _compare(previous[-1], snapshot)
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
    print(f"$ bga compare @prev @last   # {' '.join(argv[1:3])}")
    return cli_main(argv)


def _list(project: str) -> int:
    """Everything on disk, with the aliases resolution would give it.

    Incomplete captures are listed rather than hidden - they occupy the
    disk the size warning is about - but they carry no alias, because
    they are not what `@last` resolves to.
    """
    snapshots = run_store.list_snapshots(project)
    if not snapshots:
        print(f"No snapshots in {project}. "
              f"`bga snapshot -- bst build TARGET` takes one.")
        return 0
    runs = run_store.list_runs(project)
    aliases = {}
    if runs:
        aliases[runs[-1]] = "  @last"
    if len(runs) > 1:
        aliases[runs[-2]] = "  @prev"
    print(f"{len(snapshots)} snapshot(s) in {project}:")
    for path in snapshots:
        suffix = aliases.get(path, "")
        if not run_store.has_run(path):
            suffix = "  (no run directory - the build produced no elements)"
        print(f"  {os.path.basename(path)}{suffix}")
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
            f"{size / 1024 ** 3:.1f} GB. Delete snapshot directories you no "
            f"longer need - nothing else refers to them.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    sys.exit(main())
