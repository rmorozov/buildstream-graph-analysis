"""One entry point for the whole workflow (`UX-67`).

A real session used to read like this:

    python3 -m tools.bst_run_wrapped . build.log -- bst build all.bst
    python3 -m tools.bst_extract_run . build.log run/
    bga analyze run/
    python3 -m tools.bst_native_build_tracer run . native.json -- bst build
    bga correlate run/ native.json

Three different invocation styles for one linear workflow, alternating
between them at almost every step. The separation itself is right — the
analyzer is a library with a stable contract, and the tools in `tools/`
are small, independently useful programs that produce its inputs — but
that is an argument about *code layout*, not about what a user should
have to type.

So the tools keep their own `main()` and stay runnable exactly as before
(`python3 -m tools.bst_extract_run ...` is unchanged and still tested);
this module only adds a second way in, through `bga`, so the workflow
reads as one tool:

    bga wrap . build.log -- bst build all.bst
    bga extract . build.log run/
    bga analyze run/
    bga capture run . native.json -- bst build
    bga correlate run/ native.json

`UX-126` then went one step further for the local loop specifically:
those five are the plumbing, and the thing a user actually does twice a
day is

    bga snapshot -- bst build all.bst

which runs the capture, the extraction and the analysis into a
project-local store, and compares against the previous snapshot. It is
built *out of* the aliases above rather than beside them.

**Dispatch is lazy on purpose.** `importlib.import_module` is called only
for the alias actually invoked, so `bga analyze` does not pay to import
the native tracer, the Chrome-trace converters and the synthetic-run
generator on every run. Importing the table eagerly would put every
tool's import cost on the hot path of the command people run most.
"""
import importlib
import sys
from typing import Dict, List, Optional, Tuple

# alias -> (module, one-line help). Ordered as the workflow runs, because
# `bga --help` prints them in this order and that ordering is the point.
TOOL_ALIASES: Dict[str, Tuple[str, str]] = {
    "wrap": (
        "tools.bst_run_wrapped",
        "Run a command, writing a log bga can ingest",
    ),
    "extract": (
        "tools.bst_extract_run",
        "Turn a log + project into a run directory",
    ),
    "capture": (
        "tools.bst_native_build_tracer",
        "Plane 2: trace processes inside sandboxes",
    ),
    "rebuild-set": (
        "tools.bst_rebuild_set",
        "Which elements a change would force a rebuild of",
    ),
    "checkout-cost": (
        "tools.bst_checkout_cost",
        "Measure what checking out an artifact costs",
    ),
    "run-context": (
        "tools.bst_run_context",
        "Produce run-context.json on its own",
    ),
    "graph-from-show": (
        "tools.bst_show_to_graph",
        "Turn `bst show` output into graph.json",
    ),
    "timeline": (
        "tools.bga_timeline",
        "One Chrome-trace timeline, both planes",
    ),
    "log-to-chrome": (
        "tools.bst_log_to_chrome_trace",
        "Convert a BuildStream log to Chrome Trace JSON",
    ),
    "chrome-to-trace": (
        "tools.chrome_trace_to_bga_trace",
        "Convert Chrome Trace JSON to trace/v9",
    ),
    "native-to-chrome": (
        "tools.native_trace_to_chrome_trace",
        "Plane 2 trace to Chrome Trace JSON",
    ),
    "cache-logs": (
        "tools.bst_cache_logs",
        "Plane 3: mine BuildStream's own element logs",
    ),
    "cross-check": (
        "tools.bga_cross_check",
        "Cross-check an analysis against other figures",
    ),
    "gen-synthetic": (
        "tools.gen_synthetic_scale_run",
        "Generate a synthetic run directory at a scale",
    ),
    "snapshot": (
        "tools.bga_snapshot",
        "Capture, analyze and compare - the whole local loop",
    ),
    "doctor": (
        "tools.bga_doctor",
        "Check this machine can capture at all",
    ),
    "baseline": (
        "tools.bst_baseline_set",
        "Assemble a baseline set and band-compare against it",
    ),
}


def format_tool_help() -> str:
    """The alias block for `bga --help`, listing what each one wraps.

    Naming the underlying module matters: these are still separately
    usable programs, and a user who wants to script one directly (or read
    its `--help`) needs to know where it lives.
    """
    width = max(len(name) for name in TOOL_ALIASES)
    lines = [
        # "capture & conversion" undersold what is in this list: three
        # of these (`capture`, `cache-logs`, `baseline`) are whole
        # analyses with their own reports, not format converters, and a
        # reader scanning for Plane 2 or Plane 3 skipped the section
        # that has them.
        "capture, analysis and conversion (thin aliases for the programs in",
        "tools/, which remain runnable directly as `python3 -m <module>`):",
    ]
    for alias, (module, help_text) in TOOL_ALIASES.items():
        # UX-158: one line each, module included. The module used to get a
        # second line per alias, which doubled this block on the one
        # screen every user reads first - but dropping it outright was
        # wrong: these stay independently runnable, and a reader who
        # wants to script one needs to know where it lives (the test
        # above this behaviour caught that).
        lines.append(f"  {alias:<{width}}  {help_text}  ({module})")
    return "\n".join(lines)


# UX-94: the same code is importable under two names, and which one
# depends on how `bga` was installed rather than on anything the caller
# did.
#
# The directory is `tools/` in the repository and is *installed* as
# `bga._tools`, so the wheel occupies exactly one top-level name instead
# of squatting the most generic one in Python. A wheel install has no
# top-level `tools`; a source checkout has no `bga._tools`. Both are
# normal, so both are tried.
#
# **The checkout name is tried first, and that order is load-bearing.**
# An *editable* install has both, and importing the same file under two
# names produces two module objects with separate globals. Preferring
# the installed name there meant `dispatch` ran
# `bga._tools.bst_extract_run.main` while everything else in the process
# - tests that patch it, callers that imported it - held
# `tools.bst_extract_run`. CI caught it immediately: five dispatch tests
# patched a `main` that was never the one called. Trying `tools` first
# means that wherever the name resolves at all, every consumer agrees on
# one object; the installed name is reached only by a real wheel
# install, where it is the only one that exists.
_INSTALLED_PREFIX = "bga._"


def _import_tool(module_name: str):
    """Import `tools.<x>` from wherever this installation keeps it."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        # No top-level `tools` - an installed wheel. Let this one raise
        # if it fails too: it names the module that is genuinely absent.
        return importlib.import_module(_INSTALLED_PREFIX + module_name)


def dispatch(argv: List[str]) -> Optional[int]:
    """Run the tool `argv[0]` names, or return None if it names none.

    Returns None rather than raising so the caller can fall through to
    its own parser: `bga analyze` and `bga extract` have to coexist, and
    only one of them lives here.

    `sys.argv` is rewritten so the tool's own argparse reports usage as
    `bga extract ...` rather than `bst_extract_run.py ...` — a program
    that tells you to type something other than what you typed is worse
    than no help at all.
    """
    if not argv or argv[0] not in TOOL_ALIASES:
        return None
    alias = argv[0]
    module_name, _help = TOOL_ALIASES[alias]
    try:
        module = _import_tool(module_name)
    except ImportError as exc:
        # UX-77: this used to be a raw traceback on the *first* command
        # the real-project docs tell a new user to run, because
        # `pyproject.toml` packaged `bga*` only and `tools` was never
        # installed. Packaging fixes that case; this makes any remaining
        # one - a partial install, a shadowed name, a missing optional
        # dependency of the tool itself - a single actionable sentence
        # with the exit code the rest of the CLI uses for bad input.
        print(
            f"Error: `bga {alias}` could not load {module_name} ({exc}).\n"
            f"Hint: it ships with `bga` (installed as `bga._{module_name}`) - "
            f"reinstall (`pip install -e .`), or run the tool directly with "
            f"`python3 -m {module_name}` from a checkout.",
            file=sys.stderr,
        )
        # Exit 2, the code the rest of the CLI uses for "the input to
        # this invocation is wrong", not 1.
        raise SystemExit(2) from exc
    main = getattr(module, "main", None)
    if main is None:  # pragma: no cover - every listed tool has one
        raise SystemExit(f"{module_name} has no main() to dispatch to")
    saved = sys.argv
    sys.argv = [f"bga {alias}"] + list(argv[1:])
    try:
        return int(main() or 0)
    finally:
        sys.argv = saved
