"""UX-881: an operator's own wrapper directory, for a custom-prefix
toolchain PATH-shadowing can't reach (invoked by absolute path or via
`toolchain.cmake`). `bga capture run --wrapper-dir PATH [--wrapper-dir-
mode augment|replace]` threads through `BST_TRACE_WRAPPER_DIR_OVERRIDE`/
`BST_TRACE_WRAPPER_MODE` to `_wrapper_mount` (`bwrap_shim.py`), reusing
`test_the_lto_link_survives_the_jobserver.py`'s own `build_shim_argv`
harness. `TestTheTranslation` is the pure-unit half, on
`_translate_capture_wrapper_dir` (`bga/cli.py`).
"""
import os

from tests.unit.test_bwrap_shim import _fake_bwrap_with_make
from tools.native_trace.bwrap_shim import build_shim_argv

BIND_DST = "/tmp/.bst-native-trace"
_CMAKE_BST_ARGS = [
    "--unshare-pid", "--dir", "core.bst", "--chdir", "core.bst",
    "--setenv", "JOBS", "-j4", "sh", "-c", "cmake --build .",
]


def _build(real_bwrap, tmp_path, monkeypatch, **extra):
    bind_src = str(tmp_path / "host-trace-dir")
    os.makedirs(bind_src, exist_ok=True)
    monkeypatch.setenv("BST_TRACE_JOBSERVER", os.path.join(bind_src, "jobserver"))
    read_fd, write_fd = os.pipe()
    try:
        argv = build_shim_argv(
            real_bwrap=real_bwrap, bst_args=_CMAKE_BST_ARGS,
            bind_src=bind_src, bind_dst=BIND_DST,
            preload_so=f"{BIND_DST}/hook.so", trace_log=f"{BIND_DST}/trace.log",
            jobserver_fd=read_fd, element_kind="cmake", **extra)
        return argv, read_fd
    finally:
        os.close(write_fd)


def _path_value(argv):
    """The last `--setenv PATH` value - the one `_wrapper_mount` sets."""
    last = None
    for i, tok in enumerate(argv):
        if tok == "--setenv" and argv[i + 1] == "PATH":
            last = argv[i + 2]
    return last


def _ro_bind_dsts(argv):
    """Every `--ro-bind SRC DST` pair's `DST`, in argv order."""
    return [argv[i + 2] for i in range(len(argv) - 2) if argv[i] == "--ro-bind"]


SHIPPED_DST = os.path.join(BIND_DST, "wrappers")


class TestAugmentIsTheDefault:
    """No `wrapper_mode` named at all - `_wrapper_mount`'s own default."""

    def test_no_override_mounts_only_the_shipped_directory(self, tmp_path, monkeypatch):
        fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                     BIND_DST, "4.4")
        wrapper_dir = str(tmp_path / "wrappers")

        argv, read_fd = _build(fake, tmp_path, monkeypatch, wrapper_dir=wrapper_dir)
        try:
            assert _ro_bind_dsts(argv) == [SHIPPED_DST]
            assert _path_value(argv).startswith(SHIPPED_DST + ":")
        finally:
            os.close(read_fd)

    def test_an_operator_dir_augments_and_goes_first_on_path(self, tmp_path, monkeypatch):
        fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                     BIND_DST, "4.4")
        wrapper_dir = str(tmp_path / "wrappers")
        operator_dir = str(tmp_path / "operator-wrappers")

        argv, read_fd = _build(
            fake, tmp_path, monkeypatch, wrapper_dir=wrapper_dir,
            wrapper_dir_override=operator_dir, wrapper_mode="augment")
        try:
            dsts = _ro_bind_dsts(argv)
            # Two mounts: the operator's directory AND the shipped one.
            assert len(dsts) == 2
            assert SHIPPED_DST in dsts
            operator_dst = next(d for d in dsts if d != SHIPPED_DST)
            path = _path_value(argv)
            # The operator directory is first on PATH.
            assert path.split(":")[0] == operator_dst
            assert SHIPPED_DST in path.split(":")
        finally:
            os.close(read_fd)

    def test_augment_is_also_the_default_with_no_mode_named(self, tmp_path, monkeypatch):
        fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                     BIND_DST, "4.4")
        wrapper_dir = str(tmp_path / "wrappers")
        operator_dir = str(tmp_path / "operator-wrappers")

        argv, read_fd = _build(
            fake, tmp_path, monkeypatch, wrapper_dir=wrapper_dir,
            wrapper_dir_override=operator_dir)
        try:
            assert len(_ro_bind_dsts(argv)) == 2
            assert _path_value(argv).split(":")[0] != SHIPPED_DST
        finally:
            os.close(read_fd)


class TestReplace:
    def test_replace_mounts_only_the_operator_directory(self, tmp_path, monkeypatch):
        fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                     BIND_DST, "4.4")
        wrapper_dir = str(tmp_path / "wrappers")
        operator_dir = str(tmp_path / "operator-wrappers")

        argv, read_fd = _build(
            fake, tmp_path, monkeypatch, wrapper_dir=wrapper_dir,
            wrapper_dir_override=operator_dir, wrapper_mode="replace")
        try:
            dsts = _ro_bind_dsts(argv)
            assert dsts == [SHIPPED_DST]  # bound at the shipped mount point
            assert wrapper_dir not in argv
            path = _path_value(argv)
            assert path.split(":")[0] == SHIPPED_DST
        finally:
            os.close(read_fd)


class TestReplaceDropsTheShippedFltoSubdir:
    """UX-881's design: `replace` loses the shipped `flto/` subdir too -
    the operator's directory is theirs to populate."""

    def test_flto_active_replace_never_adds_the_shipped_flto_subdir(
            self, tmp_path, monkeypatch):
        monkeypatch.setenv("BST_TRACE_JOBSERVER_AUTH_MAP", "flto:core*")
        fake = _fake_bwrap_with_make(tmp_path / "real-bwrap", tmp_path / "marker",
                                     BIND_DST, "4.3")
        wrapper_dir = str(tmp_path / "wrappers")
        operator_dir = str(tmp_path / "operator-wrappers")

        argv, read_fd = _build(
            fake, tmp_path, monkeypatch, wrapper_dir=wrapper_dir,
            wrapper_dir_override=operator_dir, wrapper_mode="replace")
        try:
            flto_subdir = os.path.join(SHIPPED_DST, "flto")
            assert flto_subdir not in (_path_value(argv) or "").split(":")
        finally:
            os.close(read_fd)


# --- pure unit: bga/cli.py's _translate_capture_wrapper_dir ---------------

class TestTheTranslation:
    def setup_method(self):
        os.environ.pop("BST_TRACE_WRAPPER_DIR_OVERRIDE", None)
        os.environ.pop("BST_TRACE_WRAPPER_MODE", None)

    teardown_method = setup_method

    def test_wrapper_dir_sets_the_env_and_is_stripped_from_argv(self):
        from bga.cli import _translate_capture_wrapper_dir

        argv = ["capture", "run", "proj", "out.json", "--wrapper-dir", "/my/wrappers",
               "--", "bst", "build"]
        translated = _translate_capture_wrapper_dir(argv)

        assert os.environ["BST_TRACE_WRAPPER_DIR_OVERRIDE"] == "/my/wrappers"
        assert "--wrapper-dir" not in translated
        assert "/my/wrappers" not in translated
        assert translated == ["capture", "run", "proj", "out.json",
                              "--", "bst", "build"]

    def test_wrapper_dir_mode_sets_the_env_and_is_stripped(self):
        from bga.cli import _translate_capture_wrapper_dir

        argv = ["capture", "run", "proj", "out.json",
               "--wrapper-dir", "/my/wrappers",
               "--wrapper-dir-mode", "replace"]
        translated = _translate_capture_wrapper_dir(argv)

        assert os.environ["BST_TRACE_WRAPPER_MODE"] == "replace"
        assert "--wrapper-dir-mode" not in translated
        assert "replace" not in translated

    def test_equals_form_is_also_read(self):
        from bga.cli import _translate_capture_wrapper_dir

        argv = ["capture", "run", "proj", "out.json",
               "--wrapper-dir=/x/wrappers", "--wrapper-dir-mode=augment"]
        _translate_capture_wrapper_dir(argv)

        assert os.environ["BST_TRACE_WRAPPER_DIR_OVERRIDE"] == "/x/wrappers"
        assert os.environ["BST_TRACE_WRAPPER_MODE"] == "augment"

    def test_absent_pops_a_stale_value(self):
        from bga.cli import _translate_capture_wrapper_dir

        os.environ["BST_TRACE_WRAPPER_DIR_OVERRIDE"] = "/stale/dir"
        os.environ["BST_TRACE_WRAPPER_MODE"] = "replace"

        _translate_capture_wrapper_dir(["capture", "run", "proj", "out.json"])

        assert "BST_TRACE_WRAPPER_DIR_OVERRIDE" not in os.environ
        assert "BST_TRACE_WRAPPER_MODE" not in os.environ

    def test_not_a_capture_run_is_untouched(self):
        from bga.cli import _translate_capture_wrapper_dir

        argv = ["analyze", "run/"]
        assert _translate_capture_wrapper_dir(argv) == argv
        assert "BST_TRACE_WRAPPER_DIR_OVERRIDE" not in os.environ
