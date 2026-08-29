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

Full background: docs/guides/real-project.md
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
# `UX-378`, named in `run_store` so the layout has one authority.
HOST_SAMPLES_NAME = run_store.HOST_SAMPLES_NAME
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


def why_the_build_cannot_start(command: List[str]):
    """The sentence to print instead of capturing, or `None`.

    `UX-324`. On a machine without `bst`, `bga snapshot -- bst build
    all.bst` - the README's own first command - ran the census, launched
    the capture, and died in a 32-line traceback out of
    `subprocess.Popen`, having already created a snapshot directory with
    `build.log`, `capture-context.txt` and an empty `plane2.log` in it.
    `bga doctor` on the same machine opens with `[FAIL] bst-present` and
    a one-line remedy, so the tool *knew*; nothing asked it.

    So this asks it, and asks it **before anything is written** - which
    is why it is called from `main` rather than from `take_snapshot`:
    the snapshot directory, the sticky config and the store's
    `.gitignore` are all created on the way here, and "leaves nothing
    behind" has to mean nothing.

    `bga_doctor.check_bst` rather than a second `shutil.which`: the
    doctor's check knows about the `bst` installed beside this `bga` but
    not on PATH (`UX-150`), and a duplicate would have to learn that
    again. Only a `FAIL` refuses - an unsupported-version `WARN` is the
    doctor's to report and not a reason to decline a build.
    """
    from . import bga_doctor

    executable = command[0]
    if executable == "bst" or executable.endswith("/bst"):
        check = bga_doctor.check_bst()
        if check["status"] != bga_doctor.FAIL:
            return None
        remedy = check["remedy"] or "install BuildStream"
        return (f"Error: {check['summary']}, so this build cannot start. "
                f"Nothing was captured and nothing was written.\n"
                f"  -> {remedy}\n"
                f"  `bga doctor` checks this and everything else a capture "
                f"on this machine needs.")

    if shutil.which(executable) is None and not os.path.exists(executable):
        return (f"Error: {executable!r} is not on PATH, so this build cannot "
                f"start. Nothing was captured and nothing was written.\n"
                f"  `bga doctor` checks what a capture on this machine needs.")
    return None


def build_ever_started(snapshot: str):
    """Did the build this snapshot was taken for ever launch? Or unknown.

    `UX-324`: the store described a never-started capture as "the build
    produced no elements", which is a claim about a build that ran. The
    two are different problems - one is a broken machine and the other
    is a broken build - and the reader is told the wrong one.

    Read off the wrapper log, whose shape is fixed by
    `bst_run_wrapped.run_wrapped`: an `Executing command:` line, a
    `bga-clocks start` line, then either the build's own output or (on
    an interrupt) a `Stopping the build after ...` line. **A log that
    stops at the clock line is a build that was never launched**, and
    nothing else in that function produces one.

    `None` is a real answer and not a convenience: a snapshot with no
    wrapped log at all - a directory from before this file existed, or
    one a user assembled by hand - reads exactly like one whose build
    never ran, and saying "the build never started" of it would be the
    same overreach in the other direction as the sentence this replaces.

    Only the tail is read: a wrapped log of a real build is hundreds of
    megabytes and this runs once per row of `--list`.
    """
    path = os.path.join(snapshot, WRAPPED_LOG_NAME)
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as handle:
            handle.seek(max(0, size - 4096))
            tail = handle.read().decode("utf-8", "replace")
    except OSError:
        return None
    lines = [line for line in tail.splitlines() if line.strip()]
    if not lines:
        return None
    return "bga-clocks start" not in lines[-1]


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
    # `UX-378`: always, not behind a flag. One sample is 37 microseconds
    # and the question it answers - was the host out of memory when the
    # build slowed down - has no other source in a capture.
    argv += ["--host-samples", os.path.join(snapshot, HOST_SAMPLES_NAME)]
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

def create_parser() -> argparse.ArgumentParser:
    """`bga snapshot`'s own parser, built where a caller can reach it.

    `UX-326`: the advice block prints a `bga snapshot ...` command, and
    the only honest way to check that command is to parse it with the
    parser that will receive it. Appending `--help` to it does not work
    and is not safe - the trailing positional is
    `argparse.REMAINDER`, so `--help` lands *inside the build command*
    and the build runs. That is how this function came to exist: the
    guard's first draft ran a real capture in a unit test.
    """
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
    # UX-234: the store as a distribution rather than as a list. A
    # sibling of --list rather than a mode of it: one row per snapshot
    # and one row per host class are different documents, and a
    # consumer wanting the trend should not have to skip an aggregate
    # to reach it.
    parser.add_argument(
        "--aggregate", action="store_true",
        help="What a build here costs: min/median/p95 per host class, over "
             "the runs that finished.",
    )
    parser.add_argument(
        "--blend", action="store_true",
        help="With --aggregate: mix host classes. Refused by default.",
    )
    parser.add_argument(
        "--format", choices=("text", "json"), default="text",
        help="With --list or --aggregate: emit `store/v1` (or "
             "`store-aggregate/v1`) instead of text.",
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
        "--max-store", type=str, default=None, metavar="SIZE",
        help="With --prune: keep the store under SIZE (`2G`), oldest first.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="With --prune: say what would go, delete nothing.",
    )
    parser.add_argument(
        "--diagnose", action="store_true",
        help='Record what the bwrap shim received and exec\'d, and summarise it.'
    )
    parser.add_argument(
        "--no-inject", action="store_true",
        help='Install the shim but inject nothing - is the argv rewrite the problem?'
    )
    parser.add_argument(
        "--no-keep-raw", action="store_true",
        help="Drop the raw Plane 2 log. Kept gzipped by default; `bga "
             "timeline` needs it."
    )
    parser.add_argument(
        "--inhibit", action="store_true",
        help="Stop the machine sleeping while the build runs (systemd-inhibit). "
             "Off by default; a suspend is detected either way."
    )
    parser.add_argument(
        "--no-progress", action="store_true",
        help="No in-phase progress line. Same as BGA_NO_PROGRESS=1."
    )
    parser.add_argument("cmd", nargs=argparse.REMAINDER,
                        help="The build to run, e.g. -- bst build all.bst.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = create_parser().parse_args(argv)

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

    if args.aggregate:
        return _aggregate(project, blend=args.blend,
                          as_json=args.format == "json")

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
        prune_parser.add_argument("--max-store", type=str,
                                  default=args.max_store, metavar="SIZE",
                                  help="Delete oldest-first until the store "
                                       "is under SIZE (`2G`, `500M`).")
        prune_parser.add_argument("--dry-run", action="store_true",
                                  default=args.dry_run,
                                  help="Say what would go, delete nothing.")
        pruned = prune_parser.parse_args(rest)
        if (pruned.keep is None and pruned.older_than is None
                and pruned.max_store is None):
            print("Error: prune needs --keep N, --older-than DAYS and/or "
                  "--max-store SIZE. Nothing was deleted.", file=sys.stderr)
            return 2
        budget = None
        if pruned.max_store is not None:
            try:
                budget = parse_size(pruned.max_store)
            except ValueError as error:
                print(f"Error: {error}", file=sys.stderr)
                return 2
        return _prune(project, pruned.keep, pruned.older_than, pruned.dry_run,
                      max_store=budget)

    command = [token for token in args.cmd if token != "--"]
    if not command:
        print("Error: nothing to run. Usage: bga snapshot -- bst build TARGET",
              file=sys.stderr)
        return 2

    # UX-324: before the sticky config, before the snapshot directory,
    # before the store's .gitignore - all three are writes, and this
    # path is the one that must leave nothing.
    refusal = why_the_build_cannot_start(command)
    if refusal is not None:
        print(refusal, file=sys.stderr)
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
    _analyze(run_dir, os.path.join(snapshot, PLANE2_NAME),
             publish_to=os.path.join(snapshot, run_store.ANALYSIS_NAME))
    # UX-226: the small slice this snapshot contributes to the store's
    # per-element history. Never fatal - see `write_element_slice`.
    write_element_slice(snapshot, run_dir)

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

    _say_what_it_weighs(snapshot, project)
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


def _analyze(run_dir: str, plane2: str, publish_to: Optional[str] = None) -> int:
    """Print the report, and publish the same analysis as JSON.

    `UX-296`: **capture computes, view serves.** `bga view` used to
    re-run this analysis on every page load, which re-parsed the Plane 2
    report - measured 2.9x bytes-to-RAM, ~4.3 GB and ~30 s at the field
    capture's size, twice, before the server bound its socket. The
    analysis happens once, here, where the user is already waiting for a
    build; the page reads what it wrote.

    One analysis, two renderings (`cli.analyzed`), so publishing costs a
    `json.dumps` rather than a second pass. Falls back to the plain CLI
    path if anything about the seam is unavailable - a snapshot whose
    payload was not published is the ordinary older case, and `bga view`
    still renders it.
    """
    argv = ["analyze", run_dir]
    if os.path.isfile(plane2):
        argv += ["--plane2", plane2]

    if publish_to is None:
        from bga.cli import main as cli_main
        return cli_main(argv)

    from bga.cli import analyzed, create_parser
    from bga.report.json import format_json
    from bga.report.text import format_text

    try:
        args = create_parser().parse_args(argv)
        result = analyzed(args, None)
    except SystemExit:
        raise
    except Exception:
        from bga.cli import main as cli_main
        return cli_main(argv)

    print(format_text(result))
    try:
        with open(publish_to, "w", encoding="utf-8") as handle:
            handle.write(format_json(result))
    except OSError:
        # A published payload is a convenience on top of a capture that
        # already succeeded, the rule `write_element_slice` follows.
        pass
    return 0


# UX-226: how many elements one snapshot may remember. This is a
# *history*, not an archive - the point is to answer "did my change to
# core.bst help", not to keep a second copy of every report in the
# store. The bound is on the elements that were worth looking at: the
# critical path and the top actions of that run.
SLICE_ELEMENTS_MAX = 24
SLICE_NAME = "element-slice.json"


def write_element_slice(snapshot: str, run_dir: str) -> Optional[dict]:
    """Persist a bounded per-element slice beside the snapshot.

    Written at capture time rather than derived at read time, and the
    reason is `UX-203`'s: the store is read on **every** `bga view`, for
    every snapshot, so a row that needed an analysis would put N full
    analyses in front of a page load. The analysis has already happened
    here - `_analyze` ran a line above - so this costs one small file.

    Returns the slice, or `None` when the run could not be analyzed. A
    snapshot with no slice is the ordinary case for anything captured
    before this landed, and the reader is told so rather than shown a
    flat line at zero.
    """
    from pathlib import Path

    from bga.analyzer import BuildEfficiencyAnalyzer

    try:
        # `graph` is the narrowest section that still produces the
        # signals this slice reads, so the second analysis is the
        # cheapest one that can answer the question.
        result = BuildEfficiencyAnalyzer().analyze(Path(run_dir),
                                                   section='graph')
    except Exception:
        # A slice is a convenience on top of a capture that already
        # succeeded. It must never be the thing that fails a snapshot.
        return None
    if result is None:
        return None

    signals = getattr(result, 'signals', None) or {}
    durations = signals.get('element_durations') or {}
    from bga import schemas as _schemas
    path = list(_schemas.critical_path_uids(signals))
    # `UX-345`: `signals.critical_path_length` held this same number
    # under a `count` declaration and is gone. `sensitivity` carries it
    # under the name it has always deserved, and `section='graph'`
    # populates it.
    sensitivity = (getattr(result, 'structural', None) or {}).get('sensitivity') or {}
    path_us = sensitivity.get('critical_path_us') or 0
    headline = getattr(result, 'headline', None) or {}
    actions = [entry.get('element_uid')
               for entry in (headline.get('top_actions') or [])
               if entry.get('element_uid')]

    # Path first, then whatever the top actions add: an element on the
    # chain is the one a reader is most likely to have worked on, and
    # the order makes the cap drop the least interesting rows.
    wanted, seen = [], set()
    for uid in path + actions:
        if uid in seen:
            continue
        seen.add(uid)
        wanted.append(uid)
        if len(wanted) >= SLICE_ELEMENTS_MAX:
            break

    elements = []
    for uid in wanted:
        duration = durations.get(uid)
        elements.append({
            "element_uid": uid,
            "duration_us": duration,
            # A share of the path, and only for elements on it: an
            # element off the chain has no share of it, and publishing
            # zero would read as "on the path, costing nothing".
            "share_of_path": (duration / path_us)
                             if (uid in path and duration and path_us) else None,
            "on_critical_path": uid in path,
        })
    payload = {
        "elements": elements,
        "elements_considered": len(set(path + actions)),
        "bounded_at": SLICE_ELEMENTS_MAX,
    }
    try:
        with open(os.path.join(snapshot, SLICE_NAME), "w",
                  encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
    except OSError:
        return None
    return payload


def read_element_slice(snapshot: str) -> Optional[dict]:
    """The slice, or `None` for a snapshot written before UX-226.

    One small read, like `_run_measurements` beside it - the store must
    stay cheap enough to build on every page load.
    """
    try:
        with open(os.path.join(snapshot, SLICE_NAME), encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


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
    from bga import schemas, store_aggregate

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
            # UX-324: "never started" and "started and produced nothing"
            # are different problems and used to print the same sentence.
            "started": build_ever_started(path),
            # UX-203: what the trend was always supposed to plot. The
            # view drew `bytes` - so "is this project drifting" was
            # answered by disk usage, which is not the question. Read
            # straight off run-context rather than analysed, because
            # this runs for every snapshot on every `bga view`.
            "total_duration_us": measured.get("total_duration_us"),
            "cache_hit_rate": measured.get("cache_hit_rate"),
            # UX-226: what this run cost the elements worth watching.
            # `None`, not `[]`, for a snapshot captured before this
            # existed - the section says "no history" rather than
            # drawing a flat line at zero.
            "elements": (read_element_slice(path) or {}).get("elements"),
            # UX-296: the capacity scalars, read from the small file the
            # capture wrote beside its report. `{}` for a snapshot older
            # than that sidecar - the aggregate names the command that
            # produces one rather than parsing 1.5 GB to find out.
            "resource": run_store.read_resource_profile(path),
            # UX-234: which machine measured this, as the one compact
            # label UX-186's compared fields reduce to. The *label*
            # rather than the manifest, because this row is drawn for
            # every snapshot on every `bga view` and a manifest per row
            # is a page-weight tax for a string the reader wants. A
            # capture older than the manifest gets the "unknown host"
            # class, which is a different claim from "the same machine
            # as the others".
            "host_class": store_aggregate.host_class(
                measured.get("host_manifest")),
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

    # UX-234: read here rather than in a second pass, because this is
    # already the one small read of run-context that every row makes.
    manifest = context.get("host_manifest")
    if manifest:
        out["host_manifest"] = manifest

    build = (context.get("queue_summary") or {}).get("build") or {}
    processed, skipped = build.get("processed"), build.get("skipped")
    if isinstance(processed, int) and isinstance(skipped, int):
        total = processed + skipped
        if total:
            out["cache_hit_rate"] = skipped / total
    return out


def _mark_verdicts(rows: List[dict]) -> None:
    """Give each row a `verdict_kind` against the runs before it.

    `UX-203` asked for "the verdict vs its walk-back baseline", and its
    log claimed "the trend's colouring cannot disagree with what `bga
    compare` would say about the same pair". **That was an over-claim**,
    and `UX-214` measured it: only `compute_band` was shared. This
    function classified on the widened band's edges alone, emitted
    `within_band` - a value outside `schemas.VERDICT_KINDS` - and had no
    `UX-170` disputed-region branch at all.

    The disagreement, on the exact case the band view exists to teach:
    baselines `[100, 100, 100, 100, 200]` give a band of `[99, 101]`
    with one set edge outside it, and a candidate of `150` was coloured
    **regressed** here while `bga compare` on the same pair answered
    `within_observed_range` and declined the claim.

    One chain now: `classify_against_band`, the same function compare
    calls. The band is widened with the *median* as the reference
    total, because that is what "the baseline" means for a set rather
    than for one positional run - the widening reference differs, the
    classification does not.

    `None` below `MIN_BASELINE_RUNS`, where there is no band to judge
    against, and for any run that is not a measurement at all.
    """
    from bga.compare import classify_against_band, compute_band, widen_band

    history: List[int] = []
    for row in rows:
        duration = row.get("total_duration_us")
        if duration is None or row.get("incomplete_reason"):
            row["verdict_kind"] = None
            continue
        band = compute_band(history) if history else None
        if band is None:
            row["verdict_kind"] = None
        else:
            widened = widen_band(band, band["median_us"])
            row["verdict_kind"] = classify_against_band(duration, widened)
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


def _aggregate(project: str, blend: bool = False,
               as_json: bool = False) -> int:
    """UX-234: the store as a distribution.

    Exit `EXIT_CODE_MISMATCHED_RUNS` when the store mixes host classes
    and no blended figure was asked for - `UX-186`'s grammar, and the
    same code `bga compare` refuses a cross-host pair with, because it
    is the same refusal: these runs do not describe one thing.
    """
    from bga import store_aggregate
    from bga.cli import EXIT_CODE_MISMATCHED_RUNS

    document = store_aggregate.read(project, blend=blend)
    if as_json:
        print(json.dumps(document, indent=2))
    else:
        for line in store_aggregate.render(document):
            print(line)
    if document.get("refusal") and not blend:
        return EXIT_CODE_MISMATCHED_RUNS
    return 0


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
        if not row["has_run"] and row["started"] is False:
            # UX-324: the build was never launched. Saying "produced no
            # elements" of a build that never ran sends the reader to
            # look at their project instead of at their machine.
            suffix = "  (the build never started - nothing was captured)"
        elif not row["has_run"]:
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


_SIZE_SUFFIXES = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3,
                  "T": 1024 ** 4}


def parse_size(text: str) -> int:
    """`"2G"` -> bytes. `UX-300`'s `--max-store`.

    Binary multiples, which is what `human_bytes` prints, so a figure
    read off one command can be typed into the other. A bare number is
    bytes.
    """
    cleaned = text.strip().upper().rstrip("B")
    suffix = cleaned[-1:] if cleaned[-1:] in _SIZE_SUFFIXES else ""
    number = cleaned[:len(cleaned) - len(suffix)] if suffix else cleaned
    try:
        value = float(number)
    except ValueError:
        raise ValueError(
            f"{text!r} is not a size. Write bytes, or a number with K, M, G "
            f"or T - `--max-store 2G`.") from None
    if value < 0:
        raise ValueError(f"{text!r} is negative; a store cannot be.")
    return int(value * _SIZE_SUFFIXES[suffix])


def over_budget(snapshots: List[str], budget: int, protected: set,
                size_of) -> List[str]:
    """The oldest snapshots to delete to bring a store under `budget`.

    `UX-300`. The keep-set is not negotiable - `@last` and `@prev` are
    what the next comparison reads - so the budget is met out of what
    is left, oldest first, and a store whose protected snapshots alone
    exceed it is reported rather than emptied. Pricing, not policy:
    this returns a list, and the caller is the one that deletes.
    """
    total = sum(size_of(path) for path in snapshots)
    doomed = []
    for path in snapshots:            # oldest first, as the store lists them
        if total <= budget:
            break
        if path in protected:
            continue
        doomed.append(path)
        total -= size_of(path)
    return doomed


def _prune(project: str, keep: Optional[int], older_than: Optional[float],
           dry_run: bool, max_store: Optional[int] = None) -> int:
    """Delete snapshots by age, count or total size, never the ones
    still referred to.

    `UX-159` item 3. The store had exactly one management affordance - a
    note at 2 GB advising hand-deletion - and no command that deletes
    anything.

    `UX-300` added the third question. Age and count are proxies for the
    one a disk actually asks: a nightly capture that grew from 4 MB to
    2 GB makes `--keep 5` mean something different every month, and
    `--max-store 20G` means the same thing forever.
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
    if max_store is not None:
        # Applied to what the other rules leave, so `--keep 5
        # --max-store 20G` means "the newest five, and under 20 GiB" -
        # the stricter of the two, not the second overruling the first.
        surviving = [s for s in snapshots if s not in set(doomed)]
        doomed.extend(over_budget(surviving, max_store, protected,
                                  run_store.snapshot_size_bytes))
    doomed = [s for s in dict.fromkeys(doomed) if s not in protected]

    skipped = [s for s in snapshots if s in protected]
    if not doomed:
        print(f"Nothing to prune: {len(snapshots)} snapshot(s), "
              f"{len(skipped)} of them still referred to by @last/@prev.")
        if max_store is not None:
            held = run_store.store_size_bytes(project)
            print(f"  {run_store.human_bytes(held)} on disk, "
                  f"{'over' if held > max_store else 'within'} the "
                  f"{run_store.human_bytes(max_store)} asked for."
                  + (" Everything above it is protected by @last/@prev."
                     if held > max_store else ""))
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
    if max_store is not None:
        # What the budget leaves, said plainly: a run still over it
        # after deleting everything deletable is a fact the caller
        # needs, not a silent partial success.
        remaining = sum(run_store.snapshot_size_bytes(path)
                        for path in snapshots if path not in set(doomed))
        print(f"  {run_store.human_bytes(remaining)} would remain"
              if dry_run else
              f"  {run_store.human_bytes(remaining)} remains")
        if remaining > max_store:
            print(f"  still over the {run_store.human_bytes(max_store)} "
                  f"asked for - what is left is protected by @last/@prev, "
                  f"which the next comparison reads.")
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


def _say_what_it_weighs(snapshot: str, project: str) -> None:
    """What this capture cost on disk, and what the store now holds.

    `UX-300`. A field snapshot reached ~2 GB and nothing on the capture
    path said so: the size was discoverable by `bga snapshot --list`,
    which is a command you run *after* you have wondered. Five nightly
    captures are a quota incident scheduled in advance, and the first
    thing that makes it visible is the capture saying what it just
    wrote.

    Always, not only past a threshold. A number every time is what lets
    a reader notice the run that grew; a warning that fires once at
    2 GB tells them only that they are already there - which is the
    shape `_warn_if_large` keeps, one line further down, because "you
    are past the point where this matters" is a different sentence from
    "this one cost 4.7 MB".
    """
    try:
        size = run_store.snapshot_size_bytes(snapshot, use_cache=False)
        total = run_store.store_size_bytes(project)
        count = len(run_store.list_snapshots(project))
    except OSError:
        return
    print(f"\nThis snapshot: {run_store.human_bytes(size)}. "
          f"{run_store.runs_dir(project)}: "
          f"{run_store.human_bytes(total)} over {count} snapshot(s).",
          file=sys.stderr)
    raw = os.path.join(snapshot, RAW_LOG_NAME)
    if os.path.isfile(raw) and size:
        share = os.path.getsize(raw) / size
        if share >= 0.5:
            # UX-300 re-measured `UX-188`'s ratio at scale and found the
            # ratio unchanged (9.0% of the uncompressed log at 200,000
            # processes, against 8-12% then) while its *meaning* moved:
            # `UX-297` took the per-process records out of the report,
            # so the raw log is no longer a fraction of a snapshot
            # beside a large report - it is the snapshot. Said out loud
            # because `--no-keep-raw` looks like a small saving and is
            # now the whole one, at the price of a run whose timeline
            # can never be rendered again.
            print(f"  {share * 100:.0f}% of that is the raw Plane 2 log, "
                  f"which is what the timeline is rendered from. "
                  f"`--no-keep-raw` drops it and the timeline with it.",
                  file=sys.stderr)


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
