"""UX-67: one entry point for the workflow, without merging the code.

A real session used to alternate invocation styles at almost every step -
`python3 -m tools.bst_run_wrapped`, then `bga analyze`, then
`python3 -m tools.bst_native_build_tracer`, then `bga correlate`. The
separation of a stable analyzer library from small independent producer
programs is right; making a user type the seam is not.

The two properties that matter here are in tension, so both are pinned:
the tools must be reachable through `bga`, and they must remain runnable
directly, unchanged.
"""
import subprocess
import sys

import pytest

from bga.tools_dispatch import TOOL_ALIASES, dispatch, format_tool_help


def test_every_alias_points_at_an_importable_main():
    """A broken alias would only surface when someone ran it."""
    import importlib

    for alias, (module_name, _help) in TOOL_ALIASES.items():
        module = importlib.import_module(module_name)
        assert callable(getattr(module, "main", None)), f"{alias} -> {module_name}"


def test_a_non_alias_falls_through_rather_than_erroring():
    """`bga analyze` and `bga extract` have to coexist; only one of them
    lives in the dispatch table, so an unknown name must return None for
    the caller's own parser to handle."""
    assert dispatch(["analyze", "run/"]) is None
    assert dispatch([]) is None


def test_the_tool_sees_its_own_arguments_untouched(monkeypatch):
    """The dispatcher must not interpret a tool's flags - it does not
    know them, and teaching it would duplicate every tool's parser."""
    seen = {}

    def fake_main():
        seen["argv"] = list(sys.argv)
        return 0

    module = pytest.importorskip("tools.bst_extract_run")
    monkeypatch.setattr(module, "main", fake_main)

    assert dispatch(["extract", "proj/", "build.log", "run/", "--format", "wrapped"]) == 0
    assert seen["argv"][1:] == ["proj/", "build.log", "run/", "--format", "wrapped"]


def test_usage_names_what_the_user_typed(monkeypatch):
    """A program that tells you to type something other than what you
    typed is worse than no help at all."""
    seen = {}

    def fake_main():
        seen["prog"] = sys.argv[0]
        return 0

    module = pytest.importorskip("tools.bst_extract_run")
    monkeypatch.setattr(module, "main", fake_main)
    dispatch(["extract", "x"])

    assert seen["prog"] == "bga extract"


def test_sys_argv_is_restored_even_when_the_tool_raises(monkeypatch):
    """Otherwise one failed dispatch corrupts the process for anything
    that reads sys.argv afterwards."""
    before = list(sys.argv)

    def boom():
        raise RuntimeError("tool failed")

    module = pytest.importorskip("tools.bst_extract_run")
    monkeypatch.setattr(module, "main", boom)

    with pytest.raises(RuntimeError):
        dispatch(["extract", "x"])
    assert sys.argv == before


def test_the_exit_code_is_passed_through(monkeypatch):
    module = pytest.importorskip("tools.bst_extract_run")
    monkeypatch.setattr(module, "main", lambda: 3)

    assert dispatch(["extract", "x"]) == 3


def test_a_tool_returning_none_is_success(monkeypatch):
    """Several tools fall off the end of main() rather than returning 0."""
    module = pytest.importorskip("tools.bst_extract_run")
    monkeypatch.setattr(module, "main", lambda: None)

    assert dispatch(["extract", "x"]) == 0


def test_help_names_the_underlying_module():
    """These stay independently usable, so a reader has to be able to
    find the program an alias wraps."""
    text = format_tool_help()

    assert "tools.bst_extract_run" in text
    assert "extract" in text


def test_the_alias_reaches_the_tool_through_the_real_cli():
    """End to end through `bga`, not through the dispatcher directly."""
    result = subprocess.run(
        [sys.executable, "-m", "bga.cli", "extract", "--help"],
        capture_output=True, text=True,
    )

    assert result.returncode == 0
    assert "bga extract" in result.stdout


def test_the_tool_is_still_runnable_directly():
    """The separation is the point - `bga` adds a way in, it does not
    take one away."""
    result = subprocess.run(
        [sys.executable, "-m", "tools.bst_extract_run", "--help"],
        capture_output=True, text=True,
    )

    assert result.returncode == 0
    assert "bst_extract_run.py" in result.stdout


# --- UX-77: the front door ---------------------------------------------


def test_every_alias_names_a_module_that_is_actually_importable():
    """The defect `UX-77` was filed for, in the cheapest form that would
    have caught it.

    `pyproject.toml` packaged `bga*` only, so `tools` was never
    installed and every alias died with a raw `ModuleNotFoundError` -
    the first command the real-project docs tell a new user to run. This
    test passes from a checkout either way; the packaging itself is
    guarded by the `packaging` CI job, which runs a built wheel from an
    empty directory.
    """
    import importlib

    from bga.tools_dispatch import TOOL_ALIASES

    for alias, (module_name, _help) in TOOL_ALIASES.items():
        module = importlib.import_module(module_name)
        assert getattr(module, "main", None) is not None, (
            f"`bga {alias}` dispatches to {module_name}, which has no main()"
        )


def test_an_unimportable_tool_is_a_handled_error_not_a_traceback(monkeypatch, capsys):
    """`UX-77` required exit 2 and one actionable sentence. A raw
    traceback out of the first documented command is the failure mode
    this replaces."""
    import importlib

    import bga.tools_dispatch as dispatch_mod

    def _boom(name):
        raise ImportError("No module named 'tools'")

    monkeypatch.setattr(importlib, "import_module", _boom)

    with pytest.raises(SystemExit) as excinfo:
        dispatch_mod.dispatch(["extract", "--help"])

    assert excinfo.value.code == 2
    message = capsys.readouterr().err
    assert "could not load tools.bst_extract_run" in message
    assert "python3 -m tools.bst_extract_run" in message


def test_dispatch_and_the_rest_of_the_process_agree_on_one_module_object():
    """UX-94: `tools.<x>` and `bga._tools.<x>` are the same file, and
    importing it under both names produces two module objects with
    separate globals.

    An *editable* install has both names. The first version of the
    dispatcher preferred the installed one, so it called
    `bga._tools.bst_extract_run.main` while every test that patched
    `tools.bst_extract_run.main` - and every caller that had imported it
    - held the other object. Five dispatch tests failed in CI on exactly
    that, and passed locally, because the local environment happened to
    predate the packaging change and had only one of the two names.

    Patching through the public name and asserting the dispatcher sees
    it is the property that matters, and it holds under either layout:
    where `tools` resolves, everyone uses it; a real wheel has only
    `bga._tools` and no second object to disagree with.
    """
    import sys

    module = pytest.importorskip("tools.bst_extract_run")
    called = []
    original = module.main
    module.main = lambda: called.append(True) or 0
    try:
        assert dispatch(["extract", "proj/", "build.log", "run/"]) == 0
    finally:
        module.main = original
    assert called == [True], (
        "dispatch ran a different module object than the one patched - "
        "see UX-94: prefer the checkout name so both resolve to one object"
    )
    assert sys.argv[0] != "bga extract"  # argv restored
