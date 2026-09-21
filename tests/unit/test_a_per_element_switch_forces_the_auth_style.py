"""UX-879: a per-element `BST_TRACE_JOBSERVER_AUTH_MAP` override takes
precedence over the auto/compiler_safe/downgrade path UX-878 built -
`resolve_auth_override` (pure) and its `_jobserver_injection` call site
(integration, through `build_shim_argv`), reusing UX-878's own
`_build_cmake_with_fd` fake-bwrap-with-make harness.
"""
import os

from tests.unit.test_bwrap_shim import _fake_bwrap_with_make
from tests.unit.test_the_lto_link_survives_the_jobserver import (
    BIND_DST,
    _build_cmake_with_fd,
    _makeflags_value,
    _setenv_values,
)
from tools.native_trace.bwrap_shim import resolve_auth_override

# --- pure unit: resolve_auth_override ---------------------------------------


def test_an_element_matched_to_fd_resolves_fd():
    assert resolve_auth_override("fd:core.bst", "core.bst") == "fd"


def test_an_element_matched_to_off_resolves_off():
    assert resolve_auth_override("off:core.bst", "core.bst") == "off"


def test_an_element_matched_to_fifo_resolves_fifo():
    assert resolve_auth_override("fifo:core.bst", "core.bst") == "fifo"


def test_an_unmatched_element_resolves_none():
    assert resolve_auth_override("fd:llvm*.bst", "core.bst") is None


def test_no_map_or_no_element_resolves_none():
    assert resolve_auth_override(None, "core.bst") is None
    assert resolve_auth_override("", "core.bst") is None
    assert resolve_auth_override("fd:core.bst", None) is None


def test_first_match_wins_on_overlapping_globs():
    # `off:core.bst` also matches, but `fd:*.bst` is the first group.
    assert resolve_auth_override("fd:*.bst;off:core.bst", "core.bst") == "fd"


def test_multiple_globs_in_one_group_and_multiple_elements():
    assert resolve_auth_override("fd:llvm*.bst,make.bst;off:weird.bst",
                                 "make.bst") == "fd"
    assert resolve_auth_override("fd:llvm*.bst,make.bst;off:weird.bst",
                                 "weird.bst") == "off"


# --- integration: build_shim_argv, cmake on the Makefiles/JOBS path --------


def test_fd_override_forces_raw_auth_even_on_make_4_3(tmp_path, monkeypatch):
    """UX-878's own scrub would fire here (make 4.3, cmake, fd pool) -
    the override bypasses it outright."""
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.3")
    monkeypatch.setenv("BST_TRACE_JOBSERVER_AUTH_MAP", "fd:core.bst")

    argv, read_fd = _build_cmake_with_fd(fake, tmp_path, monkeypatch)
    try:
        value = _makeflags_value(argv)
        assert value == f"--jobserver-auth={read_fd},{read_fd}"
        assert "fifo:" not in value
    finally:
        os.close(read_fd)


def test_off_override_scrubs_with_no_wrapper_mount_and_jobs_untouched(
        tmp_path, monkeypatch):
    """Make 4.4 (not 4.3): on 4.4 the *unmatched* auto path would
    rewrite to `fifo:` (`test_cmake_fd_with_make_4_4_is_rewritten_to_fifo`
    in `test_the_lto_link_survives_the_jobserver.py`), so an `off` match
    that scrubs instead is a real assertion about the override, not
    something auto would have done anyway (make 4.3's auto path already
    scrubs on its own, and would pass this same assertion vacuously)."""
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.4")
    wrapper_dir = str(tmp_path / "wrappers")
    monkeypatch.setenv("BST_TRACE_JOBSERVER_AUTH_MAP", "off:core.bst")

    argv, read_fd = _build_cmake_with_fd(
        fake, tmp_path, monkeypatch, wrapper_dir=wrapper_dir)
    try:
        assert "MAKEFLAGS" not in argv
        assert not any("--jobserver-auth" in tok for tok in argv)
        assert "--ro-bind" not in argv
        assert _setenv_values(argv, "JOBS") == ["-j4"]
    finally:
        os.close(read_fd)


def test_fifo_override_forces_the_fifo_path(tmp_path, monkeypatch):
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.3")
    monkeypatch.setenv("BST_TRACE_JOBSERVER_AUTH_MAP", "fifo:core.bst")

    argv, read_fd = _build_cmake_with_fd(fake, tmp_path, monkeypatch)
    try:
        value = _makeflags_value(argv)
        assert value == f"--jobserver-auth=fifo:{BIND_DST}/jobserver"
    finally:
        os.close(read_fd)


def test_an_unmatched_element_on_make_4_3_is_scrubbed(tmp_path, monkeypatch):
    """Non-regression anchor: a map that names no glob for this element
    falls straight through to UX-878's own auto/scrub behaviour. Read on
    `cargo`, since UX-913 moved `cmake_meson` out of the scrubbed set -
    the anchor is "the map did not apply", and cargo is where that still
    ends in a scrub."""
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.3")
    monkeypatch.setenv("BST_TRACE_JOBSERVER_AUTH_MAP", "fd:llvm*.bst")

    argv, read_fd = _build_cmake_with_fd(fake, tmp_path, monkeypatch,
                                         element_kind="cargo")
    try:
        assert "MAKEFLAGS" not in argv
        assert not any("--jobserver-auth" in tok for tok in argv)
    finally:
        os.close(read_fd)


def test_an_unmatched_cmake_element_on_make_4_3_keeps_its_auth(
        tmp_path, monkeypatch):
    """The other half of the same anchor after UX-913: not matching the
    map must leave a cmake element on the shim route, not take its
    jobserver away. This is the case `11-serial-giant` lived in for eight
    CI pairs."""
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.3")
    monkeypatch.setenv("BST_TRACE_JOBSERVER_AUTH_MAP", "fd:llvm*.bst")

    argv, read_fd = _build_cmake_with_fd(fake, tmp_path, monkeypatch)
    try:
        assert _makeflags_value(argv) == f"--jobserver-auth={read_fd},{read_fd}"
    finally:
        os.close(read_fd)
