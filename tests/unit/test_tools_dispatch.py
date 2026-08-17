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
