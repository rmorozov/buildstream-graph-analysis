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
        "Run a command, writing a wrapper-timestamped log bga can ingest",
    ),
    "extract": (
        "tools.bst_extract_run",
        "Turn a BuildStream log + project into a run directory (the analyzer's input)",
    ),
    "capture": (
        "tools.bst_native_build_tracer",
        "Plane 2: trace processes inside element sandboxes (run/report)",
    ),
    "rebuild-set": (
        "tools.bst_rebuild_set",
        "Compute which elements a change would force a rebuild of",
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
        "Convert a Plane 2 native trace to Chrome Trace JSON",
    ),
    "cache-logs": (
        "tools.bst_cache_logs",
        "Plane 3: mine BuildStream's own persisted element logs (no capture needed)",
    ),
    "cross-check": (
        "tools.bga_cross_check",
        "Cross-check an analysis against independently derived figures",
    ),
    "gen-synthetic": (
        "tools.gen_synthetic_scale_run",
        "Generate a synthetic run directory at a chosen scale",
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
        "capture & conversion (thin aliases for the programs in tools/,",
        "which remain runnable directly as `python3 -m <module>`):",
    ]
    for alias, (module, help_text) in TOOL_ALIASES.items():
        lines.append(f"  {alias:<{width}}  {help_text}")
        lines.append(f"  {'':<{width}}  ({module})")
    return "\n".join(lines)


# UX-94: the same code is importable under two names, and which one
# depends on how `bga` was installed rather than on anything the caller
# did.
#
# The directory is `tools/` in the repository and is *installed* as
# `bga._tools`, so the wheel occupies exactly one top-level name instead
# of squatting the most generic one in Python. A source checkout has no
# `bga._tools`; an installed wheel has no top-level `tools`. Both are
# normal, so both are tried - installed name first, because that is the
# one a user who typed `pip install bga` has.
_INSTALLED_PREFIX = "bga._"


def _import_tool(module_name: str):
    """Import `tools.<x>` from wherever this installation keeps it."""
    try:
        return importlib.import_module(_INSTALLED_PREFIX + module_name)
    except ImportError:
        # Not installed under `bga._tools` - a plain source checkout.
        # Raising from here would report the *installed* name, which is
        # not the one that is missing, so let the checkout name raise.
        return importlib.import_module(module_name)


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
