"""UX-325: every documented command, run against an installed `bga`.

`UX-77` shipped a wheel whose `bga wrap` died with `ModuleNotFoundError`
for every user, because the checkout had `tools/` on `sys.path` and the
wheel did not. `UX-203` shipped the same class again in the viewer.
`UX-325` is the third: `bga snapshot --aggregate` reached the
architecture's table, the README and `docs/README.md` while dying with
`ModuleNotFoundError: No module named 'tools'` on every `pip install` -
because `bga/store_aggregate.py` said `from tools.bga_snapshot import
store_listing`, and no test ever ran that line from outside a checkout.

What kept the class alive is not the import. It is that CI's
installed-mode exercise was a **hand-written list of nineteen aliases**,
written in round 12 and never grown: `--help` each, nothing run. A
command added after it was written was not in it, and `--aggregate` is
not a command at all - it is a flag on one that was.

So this module derives the list instead:

* the **inventory** is `docs/design/architecture.md`'s command table,
  which `tests/unit/test_the_command_table_is_the_cli.py` already holds
  equal to the parser's own subcommands plus the promoted aliases. A
  command documented but not swept is a failure here, and a command
  added to the parser without a row is a failure there;
* every command `bga` will dispatch - the documented twenty-one plus
  the ten converters and internal aliases with no row - is **parsed**
  (`--help`) from an empty directory, which is what a console-script
  entry point sees and what the repo root hides. Thirty-one, against the
  nineteen the hand-list named;
* and every command carries a declared **verdict** for one real
  invocation - `OK` (exit 0), `REFUSES` (a clean one-line refusal, no
  traceback), or `PARSE_ONLY` with the reason it cannot be run in CI.
  `PARSE_ONLY` is the only judgement, it needs a written reason, and
  `tests/unit/test_no_absolute_tools_import_survives.py` keeps it a
  minority.

Run it as CI does:

    python tests/installed_command_sweep.py --bga /path/to/venv/bin/bga

`--bga` is the point: the sweep drives an **installed** entry point as a
subprocess while deriving the list from the checkout. Pointed at a
checkout's own `bga` it passes trivially, which is exactly the blindness
it exists to remove.
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
ARCHITECTURE = REPO / "docs/design/architecture.md"
FIXTURE_RUN = REPO / "tests/fixtures/macro_micro/run"

_ROW = re.compile(r"^\| `bga ([a-z-]+)", re.M)

OK = "ok"                  # exit 0 on a real invocation
REFUSES = "refuses"        # non-zero, one clean line, no traceback
PARSE_ONLY = "parse-only"  # cannot be run in CI; the reason says why


def documented_commands():
    """The inventory, read from the document a reader reads.

    Not the parser: the parser cannot tell you about `bga view`, which
    is an alias, and the aliases cannot tell you which ones are
    documented. The table is the one list that means "a reader will
    find this", and `UX-322`'s guard holds it equal to the parser.

    These are the commands that get a **real invocation**, because they
    are the ones a reader is told to run.
    """
    return frozenset(_ROW.findall(ARCHITECTURE.read_text(encoding="utf-8")))


def every_command():
    """Everything `bga` will dispatch, documented or not.

    The wider circle, and the one that gets **parsed**: eleven aliases
    are converters and internal plumbing with no row in the table
    (`UX-322` argued that out), and the step this replaced did run
    `--help` on nine of them. Losing that would have been a quiet
    narrowing, so the sweep keeps both circles rather than one.

    Read from the checkout - this module drives an installed `bga` and
    derives the list from the source tree beside it.
    """
    sys.path.insert(0, str(REPO))
    from bga import cli
    from bga.tools_dispatch import TOOL_ALIASES

    native = frozenset()
    for action in cli.create_parser()._actions:
        if getattr(action, "choices", None):
            native = frozenset(action.choices)
            break
    if not native:
        raise AssertionError("no subparser action found on the CLI parser")
    return native | frozenset(TOOL_ALIASES)


class Fixtures:
    """The smallest tree each real invocation needs, built once.

    Nothing here is a golden output - the sweep asserts that a command
    *ran*, not what it printed. Fifteen commands' worth of fixture is
    three directories.
    """

    def __init__(self, root: pathlib.Path):
        self.root = root
        self.run = root / "run"
        shutil.copytree(FIXTURE_RUN, self.run)

        # A snapshot is a run plus the two files `bga snapshot` leaves
        # beside it. `timeline` and `correlate` read the snapshot shape,
        # not the run shape, and used to be swept as neither.
        self.snapshot = root / "20260101T000000Z"
        (self.snapshot).mkdir()
        shutil.copytree(FIXTURE_RUN, self.snapshot / "run")
        (self.snapshot / "build.log").write_text("", encoding="utf-8")
        self.plane2 = self.snapshot / "plane2.json"
        self.plane2.write_text(json.dumps({
            "by_element": {}, "per_element_parallelism": [],
            "cpu_time": {"per_element": {}},
            "declared_vs_used": {"unused_candidates": []},
        }), encoding="utf-8")

        # The store `--aggregate` reads: a project with three measured
        # snapshots in it. This is the UX-325 defect's own path.
        self.store = root / "project"
        runs = self.store / ".bga" / "runs"
        for index, stamp in enumerate(("20260801T000000Z", "20260802T000000Z",
                                       "20260803T000000Z")):
            run = runs / stamp / "run"
            run.mkdir(parents=True)
            (run / "report.json").write_text(json.dumps({
                "schema": "analyze/v2",
                "producer": {"tool": "bga", "version": "0.2.0",
                             "contracts": ["analyze/v2"]},
            }), encoding="utf-8")
            (run / "run-context.json").write_text(json.dumps({
                "wall_clock": {"start_us": 0, "end_us": 1_000_000 * (index + 2)},
                "queue_summary": {"build": {"processed": 8, "skipped": 2}},
                "host_manifest": {"os": "linux", "arch": "x86_64",
                                  "cpu_count": 8, "memory_mb": 16000},
            }), encoding="utf-8")
        (self.store / "project.conf").write_text("name: sweep\n", encoding="utf-8")

        # A log that is not a wrapped log, so `extract` refuses for a
        # stated reason rather than for a missing file.
        self.not_a_log = root / "not-a-wrapped.log"
        self.not_a_log.write_text("this is not a bst build log\n", encoding="utf-8")

        self.out = root / "out"
        self.out.mkdir()
        self.empty = root / "empty"
        self.empty.mkdir()

    @property
    def element(self):
        """An element uid out of the fixture graph, rather than a name
        typed here that a regenerated fixture would silently orphan."""
        graph = json.loads((self.run / "graph.json").read_text(encoding="utf-8"))
        return graph["elements"][0]["uid"]


def invocations(fx: Fixtures):
    """command -> (verdict, argv or reason).

    Every documented command has an entry. A command whose only real
    invocation needs `bst`, a sandbox or a git remote is `PARSE_ONLY`
    with the reason written out; everything else is run.
    """
    run, snap = str(fx.run), str(fx.snapshot)
    return {
        # --- the eleven that read a run directory -------------------
        "analyze": (OK, ["analyze", run]),
        "compare": (OK, ["compare", run, run]),
        "correlate": (OK, ["correlate", run, str(fx.plane2)]),
        "floors": (OK, ["floors", run]),
        "graph": (OK, ["graph", run]),
        "utilisation": (OK, ["utilisation", run]),
        "whatif": (OK, ["whatif", run]),
        "replay": (OK, ["replay", run]),
        "diagnostics": (OK, ["diagnostics", run]),
        "cache-trend": (OK, ["cache-trend", run]),
        "sweep": (OK, ["sweep", run]),
        "blast": (OK, ["blast", fx.element, run]),

        # --- the viewer axis, which no installed-mode step ran -------
        "view": (OK, ["view", run, "--no-browser",
                      "--export", str(fx.out / "report.html")]),
        "timeline": (OK, ["timeline", snap,
                          "-o", str(fx.out / "trace.perfetto-trace")]),

        # --- UX-325's own defect ------------------------------------
        "snapshot": (OK, ["snapshot", "--aggregate", "--project", str(fx.store)]),

        # --- runs anywhere, and says what it found ------------------
        "doctor": (OK, ["doctor"]),

        # --- the two whose refusal is the reachable path ------------
        "cache-logs": (REFUSES, ["cache-logs", str(fx.empty)]),
        "extract": (REFUSES, ["extract", str(fx.empty), str(fx.not_a_log),
                              str(fx.out / "extracted")]),

        # --- and the three that cannot run on a CI runner -----------
        "capture": (PARSE_ONLY,
                    "every capture needs `bst` and a working sandbox; the "
                    "installed-capture job below is the exercise for it"),
        "wrap": (PARSE_ONLY,
                 "its only argument shape is `-- bst ...`, which needs `bst` "
                 "on PATH; the non-`bst` path raises rather than refusing, "
                 "which is UX-326's subject and not this sweep's to assert"),
        "baseline": (PARSE_ONLY,
                     "needs a git remote carrying published capture refs; "
                     "there is none on a runner and inventing one would test "
                     "the fixture"),
    }


def _run(bga, argv, cwd):
    return subprocess.run([bga, *argv], capture_output=True, text=True,
                          cwd=cwd, timeout=300)


def sweep(bga: str, verbose: bool = True) -> int:
    documented = documented_commands()
    commands = sorted(documented)
    parseable = sorted(every_command() | documented)
    failures = []
    ran = skipped = 0
    with tempfile.TemporaryDirectory() as tmp:
        fx = Fixtures(pathlib.Path(tmp))
        plan = invocations(fx)
        # An empty cwd, because a console script does not put the
        # working directory on `sys.path` - which is the whole reason
        # `from tools.` survived twenty rounds of green CI.
        cwd = str(fx.empty)

        missing = sorted(set(commands) - set(plan))
        if missing:
            failures.append(
                f"documented but not swept: {missing}. Add an entry to "
                "invocations() - PARSE_ONLY with a reason if it cannot run.")
        stale = sorted(set(plan) - set(commands))
        if stale:
            failures.append(f"swept but not documented: {stale}")

        for command in parseable:
            done = _run(bga, [command, "--help"], cwd)
            if done.returncode != 0:
                failures.append(
                    f"`bga {command} --help` exited {done.returncode}\n"
                    f"{done.stdout}{done.stderr}")
                continue
            if verbose:
                print(f"  parse   bga {command} --help")

            if command not in documented:
                continue
            verdict, detail = plan.get(command, (PARSE_ONLY, "no entry"))
            if verdict == PARSE_ONLY:
                skipped += 1
                if verbose:
                    print(f"  skip    bga {command} - {detail}")
                continue

            ran += 1
            done = _run(bga, detail, cwd)
            joined = done.stdout + done.stderr
            label = " ".join(detail[:2])
            if "Traceback (most recent call last)" in joined:
                failures.append(
                    f"`bga {label} ...` printed a traceback:\n{joined[-2000:]}")
            elif verdict == OK and done.returncode != 0:
                failures.append(
                    f"`bga {label} ...` exited {done.returncode}, expected 0\n"
                    f"{joined[-2000:]}")
            elif verdict == REFUSES and done.returncode == 0:
                failures.append(
                    f"`bga {label} ...` succeeded where the sweep records a "
                    "refusal; the entry is out of date")
            elif verbose:
                print(f"  {verdict:7s} bga {label} ... -> {done.returncode}")

    if failures:
        print(f"\n{len(failures)} failure(s) sweeping {len(parseable)} "
              f"command(s) against {bga}:\n", file=sys.stderr)
        for failure in failures:
            print(f"* {failure}\n", file=sys.stderr)
        return 1
    print(f"\n{len(parseable)} commands parsed ({len(commands)} documented), "
          f"{ran} real invocation(s) clean, {skipped} parse-only, "
          f"against {bga}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bga", required=True,
                        help="the installed `bga` entry point to drive")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    if not os.path.exists(args.bga):
        print(f"no such entry point: {args.bga}", file=sys.stderr)
        return 2
    return sweep(args.bga, verbose=not args.quiet)


if __name__ == "__main__":
    sys.exit(main())
