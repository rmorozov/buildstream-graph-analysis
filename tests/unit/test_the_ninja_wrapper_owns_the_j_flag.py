"""UX-888: the ninja wrapper is ninja's single source of `-j`. A recipe
of shape `ninja -j ${JOBS}` (the `-j` literal, `JOBS` a bare count)
becomes `ninja -j  -C _builddir` once `_ninja_aware_env` empties `JOBS`,
and ninja reads `-C` as the `-j` value and dies. The wrapper now strips
the recipe's own `-jN`/`--jobs=N`/dangling-`-j` before prepending its
token-held `-j<width>`. Runs the real `ninja` wrapper under `sh` against
a real pipe pair with a fake ninja that echoes its argv (UX-846 harness).
"""
import os
import subprocess

import pytest

from tests.unit.test_a_held_tool_returns_its_tokens import WRAPPERS, _fake_tool


@pytest.fixture(autouse=True)
def _generous_acquire_budget(monkeypatch):
    """As in UX-846's own file: assert the argv shape, not scheduling -
    give `dd`'s non-blocking reads room past the 50ms production budget
    under `make test`'s xdist contention."""
    monkeypatch.setenv("BGA_WRAPPER_ACQUIRE_MS", "2000")


def _run_ninja(tmp_path, args, tokens=2):
    """The real `ninja` wrapper over a fake ninja, a pipe pair seeded
    with `tokens`. Returns the argv the fake ninja actually received."""
    r, w = os.pipe()
    os.write(w, b"+" * tokens)
    os.set_inheritable(r, True)
    os.set_inheritable(w, True)
    out, marker = tmp_path / "out", tmp_path / "marker"
    _fake_tool(tmp_path, "ninja", marker, out, hang=False)
    env = dict(os.environ)
    env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
    env["MAKEFLAGS"] = f"--jobserver-auth={r},{w}"
    env["BST_TRACE_WRAPPER_CAP"] = "8"
    try:
        result = subprocess.run(["sh", str(WRAPPERS / "ninja"), *args], env=env,
                                 pass_fds=(r, w), capture_output=True, text=True,
                                 timeout=10)
    finally:
        os.close(r)
        os.close(w)
    assert result.returncode == 0, (result.stdout, result.stderr)
    return out.read_text().strip().split()


def _j_flags(argv):
    """The parallelism flags in `argv` - the wrapper's own bare `-j`
    (its width follows as a separate token), a glued `-jN`, `--jobs=N`."""
    return [tok for tok in argv
            if tok == "-j" or tok.startswith("-j") or tok.startswith("--jobs=")]


class TestTheWrapperOwnsTheJFlag:
    def test_a_dangling_j_from_an_emptied_jobs_is_stripped(self, tmp_path):
        """The field bug: `ninja -v -j ${JOBS} -C _builddir` with `JOBS`
        emptied to `ninja -v -j -C _builddir`. The stray `-j` (before the
        non-integer `-C`) is dropped; the wrapper's own `-j 3` is the only
        one, and `-C _builddir` survive."""
        argv = _run_ninja(tmp_path, ["-v", "-j", "-C", "_builddir"])
        assert _j_flags(argv) == ["-j"], argv
        assert "-j 3" in " ".join(argv), argv  # 2 held + 1 implicit
        assert "-C" in argv and "_builddir" in argv, argv
        assert "-v" in argv, argv

    def test_an_explicit_dash_j_number_is_stripped(self, tmp_path):
        argv = _run_ninja(tmp_path, ["-j", "8", "build"])
        assert _j_flags(argv) == ["-j"], argv
        assert "-j 3" in " ".join(argv), argv
        assert "8" not in argv, argv          # the recipe's count is gone
        assert "build" in argv, argv

    def test_a_glued_dash_jn_is_stripped(self, tmp_path):
        argv = _run_ninja(tmp_path, ["-j8", "build"])
        assert _j_flags(argv) == ["-j"], argv  # only the wrapper's bare -j
        assert "build" in argv, argv

    def test_a_long_jobs_flag_is_stripped(self, tmp_path):
        argv = _run_ninja(tmp_path, ["--jobs=8", "build"])
        assert _j_flags(argv) == ["-j"], argv
        assert "build" in argv, argv

    def test_a_recipe_with_no_j_is_left_alone(self, tmp_path):
        """No recipe `-j` at all (the cmake `ninja ${JOBS}` shape once
        `JOBS` empties): the wrapper adds exactly its own, nothing else
        is touched."""
        argv = _run_ninja(tmp_path, ["-C", "_builddir"])
        assert _j_flags(argv) == ["-j"], argv
        assert argv.count("-C") == 1 and "_builddir" in argv, argv
