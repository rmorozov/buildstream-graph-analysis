"""UX-880: a forced `fd` auth on an element that does GCC LTO ICEs
(`opts-common.cc:2123`, round 125) - `lto-wrapper`, a grandchild across
bwrap, cannot open the raw fd. The `flto` override keeps `fd` for
`make` itself (unlike `off`) and mounts a GCC-driver shim that strips
the auth before it reaches the compiler, capping an already-requested
`-flto` to a static `$BST_TRACE_LTO_CAP` instead. Class 1 runs the real
shim script under `sh` (`test_a_held_tool_returns_its_tokens.py`'s own
harness); class 2 goes through `build_shim_argv` on a make-4.3 fixture
(`test_the_lto_link_survives_the_jobserver.py`'s own harness).

Verifier fix: the shim scripts sit in the one wrapper directory every
jobserver-active sandbox mounts (UX-846), so they are on `PATH` for
every element, matched or not - `TestTheShimIsGatedOnFltoActive` guards
that an unmatched element's compiler invocation is untouched
(`BST_TRACE_FLTO_ACTIVE` unset), and the `build_shim_argv` tests assert
the flag is set only for a `flto:`-matched element.
"""
import os
import pathlib
import subprocess

from tests.unit.test_bwrap_shim import _fake_bwrap_with_make
from tools.native_trace.bwrap_shim import build_shim_argv

REPO = pathlib.Path(__file__).resolve().parents[2]
WRAPPERS = REPO / "tools/native_trace/wrappers"
BIND_DST = "/tmp/.bst-native-trace"


# --- class 1: the reference shim script, run under sh ----------------------

def _fake_compiler(bin_dir, name, out):
    """Echoes its own `MAKEFLAGS` and argv, `|`-separated, to `out`."""
    tool = bin_dir / name
    tool.write_text(
        "#!/bin/sh\n"
        f'printf \'%s|%s\\n\' "$MAKEFLAGS" "$*" > "{out}"\n'
    )
    tool.chmod(0o755)


def _run_gcc(tmp_path, argv, makeflags, lto_cap=None, flto_active=True):
    """`flto_active` (verifier fix): defaults on, since most of this
    class exercises the transform itself - the gate's own off/on
    contrast lives in `TestTheShimIsGatedOnFltoActive` below."""
    _fake_compiler(tmp_path, "gcc", tmp_path / "out")
    env = dict(os.environ)
    env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
    env["MAKEFLAGS"] = makeflags
    if lto_cap is not None:
        env["BST_TRACE_LTO_CAP"] = lto_cap
    else:
        env.pop("BST_TRACE_LTO_CAP", None)
    if flto_active:
        env["BST_TRACE_FLTO_ACTIVE"] = "1"
    else:
        env.pop("BST_TRACE_FLTO_ACTIVE", None)
    result = subprocess.run(["sh", str(WRAPPERS / "gcc"), *argv], env=env,
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, (result.stdout, result.stderr)
    makeflags_out, argv_out = (tmp_path / "out").read_text().rstrip("\n").split("|", 1)
    return makeflags_out, argv_out


class TestTheShimRewritesFltoAndStripsTheAuth:
    """`BST_TRACE_FLTO_ACTIVE=1` throughout - this class guards the
    transform itself, on the matched-element side of the gate."""

    def test_bare_flto_is_rewritten_to_the_cap_and_auth_is_stripped(self, tmp_path):
        makeflags, argv = _run_gcc(
            tmp_path, ["-flto", "-c", "x.c"],
            "--jobserver-auth=3,4 -j8", lto_cap="4")

        assert "-flto=4" in argv.split()
        assert "-flto" not in argv.split()
        assert "--jobserver-auth" not in makeflags
        assert "-j8" in makeflags

    def test_flto_jobserver_and_flto_auto_are_also_rewritten(self, tmp_path):
        for spelling in ("-flto=jobserver", "-flto=auto"):
            _, argv = _run_gcc(
                tmp_path, [spelling, "-c", "x.c"],
                "--jobserver-auth=3,4 -j8", lto_cap="6")
            assert "-flto=6" in argv.split()
            assert spelling not in argv.split()

    def test_no_flto_passes_argv_through_unchanged_and_still_strips_auth(
            self, tmp_path):
        makeflags, argv = _run_gcc(
            tmp_path, ["-c", "x.c", "-O2"],
            "--jobserver-auth=3,4 -j8", lto_cap="4")

        assert argv == "-c x.c -O2"
        assert "--jobserver-auth" not in makeflags
        assert "-j8" in makeflags


# --- verifier fix: the gate itself, the leak the shared directory risked ---
#
# The real regression: an *unmatched* element on a working dynamic-fifo
# jobserver build must see its own compiler untouched, even though the
# shim script is on its `PATH` too (UX-846's directory is shared, not
# per-element).

class TestTheShimIsGatedOnFltoActive:
    def test_unset_is_a_pure_pass_through_even_with_flto_in_argv(self, tmp_path):
        makeflags, argv = _run_gcc(
            tmp_path, ["-flto", "-c", "x.c"],
            "--jobserver-auth=fifo:/tmp/x.fifo -j8",
            lto_cap="4", flto_active=False)

        assert argv == "-flto -c x.c"
        assert makeflags == "--jobserver-auth=fifo:/tmp/x.fifo -j8"

    def test_set_to_1_strips_the_auth_and_rewrites_flto(self, tmp_path):
        makeflags, argv = _run_gcc(
            tmp_path, ["-flto", "-c", "x.c"],
            "--jobserver-auth=fifo:/tmp/x.fifo -j8",
            lto_cap="4", flto_active=True)

        assert argv == "-flto=4 -c x.c"
        assert "--jobserver-auth" not in makeflags
        assert "-j8" in makeflags


# --- class 2: through build_shim_argv, a make-4.3 fixture -------------------
#
# `--dir <name>.bst` names the element `resolve_auth_override` matches
# `BST_TRACE_JOBSERVER_AUTH_MAP` against; `element_kind="cmake"` is a
# `_COMPILER_SAFE_POLICIES` kind - scrubbed under 4.3 make on the auto
# path (UX-878's own anchor), which is exactly the contrast this guards.

def _bst_args(element):
    return [
        "--unshare-pid", "--dir", f"{element}.bst", "--chdir", f"{element}.bst",
        "--setenv", "JOBS", "-j4", "sh", "-c", "cmake --build .",
    ]


def _build(real_bwrap, tmp_path, element, wrapper_dir, monkeypatch, element_kind="cmake"):
    bind_src = str(tmp_path / "host-trace-dir")
    os.makedirs(bind_src, exist_ok=True)
    # UX-878's own scrub only fires once it can name a host FIFO to
    # rewrite `fd` to - `_compiler_safe_fifo_host`'s last resort,
    # `BST_TRACE_JOBSERVER`, the same channel the anchor's own harness
    # sets (`test_the_lto_link_survives_the_jobserver.py`).
    monkeypatch.setenv("BST_TRACE_JOBSERVER", os.path.join(bind_src, "jobserver"))
    read_fd, write_fd = os.pipe()
    try:
        argv = build_shim_argv(
            real_bwrap=real_bwrap, bst_args=_bst_args(element),
            bind_src=bind_src, bind_dst=BIND_DST,
            preload_so=f"{BIND_DST}/hook.so", trace_log=f"{BIND_DST}/trace.log",
            jobserver_fd=read_fd, element_kind=element_kind, wrapper_dir=wrapper_dir)
        return argv, read_fd
    finally:
        os.close(write_fd)


def _makeflags_value(argv):
    idx = argv.index("MAKEFLAGS")
    return argv[idx + 1]


class TestAFltoMatchedElementKeepsFdAndIsNotScrubbed:
    def test_matched_element_emits_raw_fd_and_mounts_the_wrapper(
            self, tmp_path, monkeypatch):
        monkeypatch.setenv("BST_TRACE_JOBSERVER_AUTH_MAP", "flto:llvm*")
        fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                     BIND_DST, "4.3")
        wrapper_dir = str(tmp_path / "wrappers")

        argv, read_fd = _build(fake, tmp_path, "llvm", wrapper_dir, monkeypatch)
        try:
            assert _makeflags_value(argv) == f"--jobserver-auth={read_fd},{read_fd}"
            assert "--ro-bind" in argv
            assert wrapper_dir in argv
            # Verifier fix: the flag that gates the shared-directory GCC
            # shim to only this matched element.
            assert "BST_TRACE_FLTO_ACTIVE" in argv
            flag_idx = argv.index("BST_TRACE_FLTO_ACTIVE")
            assert argv[flag_idx + 1] == "1"
        finally:
            os.close(read_fd)

    def test_unmatched_element_on_the_same_4_3_make_is_still_scrubbed(
            self, tmp_path, monkeypatch):
        """The UX-878 anchor: `flto:llvm*` naming a different element must
        not widen the scrub for one it does not match."""
        monkeypatch.setenv("BST_TRACE_JOBSERVER_AUTH_MAP", "flto:llvm*")
        fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                     BIND_DST, "4.3")
        wrapper_dir = str(tmp_path / "wrappers")

        argv, read_fd = _build(fake, tmp_path, "other", wrapper_dir, monkeypatch)
        try:
            assert "MAKEFLAGS" not in argv
            assert not any("--jobserver-auth" in tok for tok in argv)
            assert "--ro-bind" not in argv
        finally:
            os.close(read_fd)

    def test_unmatched_element_wrapper_mounted_for_other_reasons_gets_no_flag(
            self, tmp_path, monkeypatch):
        """The regression the verifier caught: a `make`-kind element is
        never scrubbed (`_compiler_safe_makeflags` excludes it) so its
        wrapper directory still mounts (held-tool coverage, UX-846) even
        though `flto:llvm*` does not match it - `BST_TRACE_FLTO_ACTIVE`
        must not ride along on that unrelated mount."""
        monkeypatch.setenv("BST_TRACE_JOBSERVER_AUTH_MAP", "flto:llvm*")
        fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                     BIND_DST, "4.3")
        wrapper_dir = str(tmp_path / "wrappers")

        argv, read_fd = _build(fake, tmp_path, "other", wrapper_dir, monkeypatch,
                               element_kind="make")
        try:
            assert _makeflags_value(argv) == f"--jobserver-auth={read_fd},{read_fd}"
            assert "--ro-bind" in argv, "held-tool coverage still mounts the directory"
            assert "BST_TRACE_FLTO_ACTIVE" not in argv
        finally:
            os.close(read_fd)
