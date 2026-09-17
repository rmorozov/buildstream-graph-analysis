"""UX-882: a `public: bga: jobserver-auth:` annotation is a second,
in-tree *source* for UX-879's four override styles, resolved AFTER the
command-line `--jobserver-auth-override` and before auto:
`resolve_auth_override(cmdline, element) or _annotation_style(element)`
in `_jobserver_injection`. This guards `_public_auth_style` (pure, the
`%{public}` YAML -> style parse) and the `_annotation_style` fallback
through `build_shim_argv` (integration), reusing UX-878/879's own
fake-bwrap-with-make harness.
"""
import json
import os

from tests.unit.test_bwrap_shim import _fake_bwrap_with_make
from tests.unit.test_the_lto_link_survives_the_jobserver import (
    BIND_DST,
    _build_cmake_with_fd,
    _makeflags_value,
)
from tools.bst_native_build_tracer import _public_auth_style

# --- pure unit: the %{public} YAML -> style parse ---------------------------


def test_a_bga_jobserver_auth_block_parses_to_its_style():
    assert _public_auth_style("bga:\n  jobserver-auth: off\n") == "off"


def test_public_with_no_bga_key_parses_to_none():
    assert _public_auth_style("bst:\n  max-jobs: 4\n") is None


def test_malformed_public_yaml_parses_to_none_without_raising():
    assert _public_auth_style(": not: valid: yaml: [") is None


def test_a_style_outside_the_four_overrides_parses_to_none():
    assert _public_auth_style("bga:\n  jobserver-auth: keep\n") is None


# --- integration: build_shim_argv, cmake on the Makefiles/JOBS path --------
#
# Make 4.4 throughout: auto would rewrite to `fifo:` here
# (`test_cmake_fd_with_make_4_4_is_rewritten_to_fifo`), so an annotation
# result that differs from that is a real assertion about the
# annotation, not something auto would have produced anyway.


def _write_auth_map(tmp_path, mapping):
    path = tmp_path / "element_auth_map.json"
    path.write_text(json.dumps(mapping))
    return str(path)


def test_an_off_annotation_scrubs_where_auto_would_fifo(tmp_path, monkeypatch):
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.4")
    monkeypatch.setenv("BST_TRACE_ELEMENT_AUTH_MAP",
                       _write_auth_map(tmp_path, {"core.bst": "off"}))
    wrapper_dir = str(tmp_path / "wrappers")

    argv, read_fd = _build_cmake_with_fd(
        fake, tmp_path, monkeypatch, wrapper_dir=wrapper_dir)
    try:
        assert "MAKEFLAGS" not in argv
        assert not any("--jobserver-auth" in tok for tok in argv)
    finally:
        os.close(read_fd)


def test_a_command_line_override_beats_the_annotation(tmp_path, monkeypatch):
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.4")
    monkeypatch.setenv("BST_TRACE_ELEMENT_AUTH_MAP",
                       _write_auth_map(tmp_path, {"core.bst": "off"}))
    monkeypatch.setenv("BST_TRACE_JOBSERVER_AUTH_MAP", "fd:core.bst")

    argv, read_fd = _build_cmake_with_fd(fake, tmp_path, monkeypatch)
    try:
        value = _makeflags_value(argv)
        assert value == f"--jobserver-auth={read_fd},{read_fd}"
        assert "fifo:" not in value
    finally:
        os.close(read_fd)


def test_an_element_in_neither_map_falls_to_auto(tmp_path, monkeypatch):
    fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                 BIND_DST, "4.4")
    monkeypatch.setenv("BST_TRACE_ELEMENT_AUTH_MAP",
                       _write_auth_map(tmp_path, {"llvm.bst": "off"}))

    argv, read_fd = _build_cmake_with_fd(fake, tmp_path, monkeypatch)
    try:
        value = _makeflags_value(argv)
        assert value == f"--jobserver-auth=fifo:{BIND_DST}/jobserver"
    finally:
        os.close(read_fd)
