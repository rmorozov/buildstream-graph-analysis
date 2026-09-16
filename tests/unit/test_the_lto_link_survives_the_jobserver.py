"""UX-878: `gcc -flto`'s lto-wrapper and cargo read `MAKEFLAGS` directly
(unwrapped by design, `bst_native_build_tracer.py:1249`) - a raw `fd`
auth is only valid for a direct child, and gcc's lto-wrapper is a deep
grandchild (measured live: GCC-13 ICE, `opts-common.cc:2123`). This
guards `compiler_safe_auth` (pure) and its `_jobserver_injection` call
site (integration, through `build_shim_argv`), reusing
`tests/unit/test_bwrap_shim.py`'s own fake-bwrap-with-make harness.
"""
import os

from tests.unit.test_bwrap_shim import _fake_bwrap_with_make, _fake_real_bwrap
from tools.native_trace.bwrap_shim import (
    _resolve_proxy_auth,
    build_shim_argv,
    compiler_safe_auth,
)

BIND_DST = "/tmp/.bst-native-trace"
_CMAKE_BST_ARGS = [
    "--unshare-pid", "--dir", "core.bst", "--chdir", "core.bst",
    "--setenv", "JOBS", "-j4", "sh", "-c", "cmake --build .",
]


# --- pure unit: compiler_safe_auth ------------------------------------------

def test_an_fd_auth_with_no_sub_4_4_make_is_rewritten_to_fifo():
    safe = compiler_safe_auth(
        "--jobserver-auth=7,7", "/tmp/.bst-native-trace/jobserver",
        make_below_44=False)

    assert safe == "--jobserver-auth=fifo:/tmp/.bst-native-trace/jobserver"
    assert "7,7" not in safe


def test_an_fd_auth_with_a_sub_4_4_make_is_scrubbed():
    safe = compiler_safe_auth(
        "--jobserver-auth=7,7", "/tmp/.bst-native-trace/jobserver",
        make_below_44=True)

    assert safe is None


def test_a_fifo_auth_stands_whatever_make_below_44_says():
    for make_below_44 in (True, False):
        safe = compiler_safe_auth(
            "--jobserver-auth=fifo:/tmp/.bst-native-trace/jobserver",
            "/tmp/.bst-native-trace/jobserver", make_below_44)

        assert safe == "--jobserver-auth=fifo:/tmp/.bst-native-trace/jobserver"


# --- integration: build_shim_argv, cmake on the Makefiles/JOBS path --------
#
# `BST_TRACE_JOBSERVER` monkeypatched to the host FIFO path an `fd` auth
# would have been opened from (`open_jobserver_fd`) - the recovery
# channel `_compiler_safe_makeflags` falls back to once the fd style has
# already consumed the FIFO entry out of `pool`.

def _fake_bwrap_make_absent(path, marker):
    """`make --version` fails (exit 127) - no sandbox make at all, the
    `probe.available=False` case `make_below_44` treats as safe to
    rewrite (an absent make cannot reject `fifo:`)."""
    body = 'case "$*" in\n  *"make --version") exit 127 ;;\nesac\nexit 0\n'
    return _fake_real_bwrap(path, marker, body)


def _makeflags_value(argv):
    idx = argv.index("MAKEFLAGS")
    return argv[idx + 1]


def _build_cmake_with_fd(real_bwrap, tmp_path, monkeypatch, element_kind="cmake",
                         **extra):
    bind_src = str(tmp_path / "host-trace-dir")
    os.makedirs(bind_src, exist_ok=True)
    jobserver_path = os.path.join(bind_src, "jobserver")
    monkeypatch.setenv("BST_TRACE_JOBSERVER", jobserver_path)
    read_fd, write_fd = os.pipe()
    try:
        argv = build_shim_argv(
            real_bwrap=real_bwrap, bst_args=_CMAKE_BST_ARGS,
            bind_src=bind_src, bind_dst=BIND_DST,
            preload_so=f"{BIND_DST}/hook.so", trace_log=f"{BIND_DST}/trace.log",
            jobserver_fd=read_fd, element_kind=element_kind, **extra)
        return argv, read_fd
    finally:
        os.close(write_fd)


def test_cmake_fd_with_make_absent_is_rewritten_to_fifo(tmp_path, monkeypatch):
    fake = _fake_bwrap_make_absent(tmp_path / "real-bwrap", tmp_path / "marker")

    argv, read_fd = _build_cmake_with_fd(fake, tmp_path, monkeypatch)
    try:
        value = _makeflags_value(argv)
        assert value == f"--jobserver-auth=fifo:{BIND_DST}/jobserver"
        assert f"{read_fd}," not in value
    finally:
        os.close(read_fd)


def test_cmake_fd_with_make_4_4_is_rewritten_to_fifo(tmp_path, monkeypatch):
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.4")

    argv, read_fd = _build_cmake_with_fd(fake, tmp_path, monkeypatch)
    try:
        value = _makeflags_value(argv)
        assert value == f"--jobserver-auth=fifo:{BIND_DST}/jobserver"
        assert f"{read_fd}," not in value
    finally:
        os.close(read_fd)


def test_cmake_fd_with_make_4_3_is_scrubbed_with_no_wrapper_mount(
        tmp_path, monkeypatch):
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.3")
    wrapper_dir = str(tmp_path / "wrappers")

    argv, read_fd = _build_cmake_with_fd(
        fake, tmp_path, monkeypatch, wrapper_dir=wrapper_dir)
    try:
        assert "MAKEFLAGS" not in argv
        assert not any("--jobserver-auth" in tok for tok in argv)
        assert "--ro-bind" not in argv
    finally:
        os.close(read_fd)


def test_cmake_fifo_style_passes_through_unchanged(tmp_path, monkeypatch):
    """The auth is already `fifo:` (no downgrade fired, e.g. sandbox make
    stayed 4.4) - `compiler_safe_auth`'s own no-op branch, reached
    through the real call site rather than asserted in isolation."""
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.4")
    bind_src = str(tmp_path / "host-trace-dir")
    os.makedirs(bind_src)
    fifo_path = os.path.join(bind_src, "jobserver")
    os.mkfifo(fifo_path)
    monkeypatch.delenv("BST_TRACE_JOBSERVER", raising=False)

    argv = build_shim_argv(
        real_bwrap=fake, bst_args=_CMAKE_BST_ARGS,
        bind_src=bind_src, bind_dst=BIND_DST,
        preload_so=f"{BIND_DST}/hook.so", trace_log=f"{BIND_DST}/trace.log",
        jobserver_fifo=fifo_path, element_kind="cmake")

    assert _makeflags_value(argv) == f"--jobserver-auth=fifo:{BIND_DST}/jobserver"


# --- one input class for cargo ----------------------------------------------

def test_cargo_fd_with_make_4_3_is_also_scrubbed(tmp_path, monkeypatch):
    """UX-878's Out of Scope: cargo's own jobserver client is unverified
    in the field, so it gets the same conservative policy as cmake/meson
    - locked here rather than widened without a live check."""
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.3")

    argv, read_fd = _build_cmake_with_fd(fake, tmp_path, monkeypatch,
                                         element_kind="cargo")
    try:
        assert "MAKEFLAGS" not in argv
        assert not any("--jobserver-auth" in tok for tok in argv)
        assert "CARGO_BUILD_JOBS" in argv  # still unset, independent of the auth
    finally:
        os.close(read_fd)


# --- UX-878 (verifier fix): a UX-849 per-element proxy under fd style ------
#
# `_resolve_proxy_auth` discards the proxy's own FIFO path when the auth
# style is `fd` (the `auto` default) - `pool["proxy_fifo"]` comes back
# `None`, so the rewrite must re-derive the path from
# `BST_TRACE_PROXY_DIR` + the element rather than fall through to the
# *global* `BST_TRACE_JOBSERVER`, a different FIFO the proxy exists
# specifically not to be.

def _build_cmake_with_proxy(real_bwrap, tmp_path, monkeypatch, **extra):
    """A proxy active in `fd` style (`BST_TRACE_JOBSERVER_AUTH=fd`, the
    `auto` default) for element `core.bst`, plus a *different* global
    `BST_TRACE_JOBSERVER` still set - the exact shape a `--plan` capture
    produces (both coexist; `_jobserver_injection`'s own "proxy wins
    outright" precedence is what this guards)."""
    monkeypatch.setenv("BST_TRACE_JOBSERVER_AUTH", "fd")
    bind_src = str(tmp_path / "host-trace-dir")
    proxy_dir = os.path.join(bind_src, "proxies")
    os.makedirs(proxy_dir, exist_ok=True)
    monkeypatch.setenv("BST_TRACE_PROXY_DIR", proxy_dir)
    proxy_fifo_path = os.path.join(proxy_dir, "core.bst.fifo")
    os.mkfifo(proxy_fifo_path)
    global_fifo_path = os.path.join(bind_src, "global-jobserver")
    os.mkfifo(global_fifo_path)
    monkeypatch.setenv("BST_TRACE_JOBSERVER", global_fifo_path)

    proxy_fd, proxy_fifo = _resolve_proxy_auth(proxy_fifo_path)
    assert proxy_fifo is None and proxy_fd is not None, (
        "fd style discards the path - the exact gap this test guards")
    try:
        argv = build_shim_argv(
            real_bwrap=real_bwrap, bst_args=_CMAKE_BST_ARGS,
            bind_src=bind_src, bind_dst=BIND_DST,
            preload_so=f"{BIND_DST}/hook.so", trace_log=f"{BIND_DST}/trace.log",
            proxy_fd=proxy_fd, proxy_fifo=proxy_fifo, element_kind="cmake", **extra)
        return argv
    finally:
        os.close(proxy_fd)


def test_cmake_proxy_under_fd_style_rewrites_to_the_proxys_own_fifo(
        tmp_path, monkeypatch):
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.4")

    argv = _build_cmake_with_proxy(fake, tmp_path, monkeypatch)

    value = _makeflags_value(argv)
    assert value == f"--jobserver-auth=fifo:{BIND_DST}/proxies/core.bst.fifo"
    assert "global-jobserver" not in value


def test_cmake_proxy_under_fd_style_with_sub_4_4_make_is_scrubbed(
        tmp_path, monkeypatch):
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.3")

    argv = _build_cmake_with_proxy(fake, tmp_path, monkeypatch)

    assert "MAKEFLAGS" not in argv
    assert not any("--jobserver-auth" in tok for tok in argv)


# --- non-regression: a pure make/autotools element is untouched ------------

def test_a_make_kind_element_keeps_its_raw_fd_auth(tmp_path, monkeypatch):
    """UX-874's own narrowing tests guard the downgrade itself; this
    guards that UX-878's new layer never reaches a `make`-kind element at
    all - its MAKEFLAGS consumer is make itself, a direct child, for
    which the fd is valid (Required Fix)."""
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.3")
    bind_src = str(tmp_path / "host-trace-dir")
    os.makedirs(bind_src, exist_ok=True)
    monkeypatch.setenv("BST_TRACE_JOBSERVER", os.path.join(bind_src, "jobserver"))
    read_fd, write_fd = os.pipe()
    try:
        argv = build_shim_argv(
            real_bwrap=fake,
            bst_args=["--unshare-pid", "--dir", "core.bst", "--chdir", "core.bst",
                     "sh", "-c", "make"],
            bind_src=bind_src, bind_dst=BIND_DST,
            preload_so=f"{BIND_DST}/hook.so", trace_log=f"{BIND_DST}/trace.log",
            jobserver_fd=read_fd, element_kind="make")

        value = _makeflags_value(argv)
        assert value == f"--jobserver-auth={read_fd},{read_fd}"
    finally:
        os.close(write_fd)
        os.close(read_fd)
