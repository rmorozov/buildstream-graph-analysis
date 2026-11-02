"""UX-1374: the hook and spine build with `$CC`, else the first of cc, gcc, clang; a named `$CC` never falls back."""

import json
import os
import shutil
import subprocess
import sys
import zipfile

import pytest

from tools import bst_native_build_tracer as tracer
from tools.native_trace import prebuilt as native_prebuilt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLANG = shutil.which("clang")
needs_clang = pytest.mark.skipif(CLANG is None, reason="no clang on PATH")


@pytest.fixture
def no_prebuilt(tmp_path, monkeypatch):
    monkeypatch.setattr(native_prebuilt, "PREBUILT_DIR", str(tmp_path / "absent"))


def _only(tmp_path, **names):
    """A PATH directory holding only the named links, e.g. clang=/usr/bin/clang."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, target in names.items():
        (bin_dir / name).symlink_to(target)
    return str(bin_dir)


class TestTheChoice:
    def test_cc_is_split_like_a_shell_word_list(self):
        sh = shutil.which("sh")
        assert native_prebuilt.compiler({"CC": "sh -O0", "PATH": os.path.dirname(sh)}) == ([sh, "-O0"], None)

    def test_a_named_cc_that_is_missing_does_not_fall_back(self, tmp_path):
        path = _only(tmp_path, cc=shutil.which("sh"))
        cc, reason = native_prebuilt.compiler({"CC": "no-such-compiler", "PATH": path})
        assert cc is None
        assert reason == "CC='no-such-compiler' is not on PATH"

    def test_without_cc_the_first_candidate_on_path_wins(self, tmp_path):
        path = _only(tmp_path, clang=shutil.which("sh"))
        assert native_prebuilt.compiler({"PATH": path}) == ([os.path.join(path, "clang")], None)

    def test_none_names_every_candidate(self, tmp_path):
        assert native_prebuilt.compiler({"PATH": str(tmp_path)}) == (
            None,
            "no C compiler (cc/gcc/clang) found on PATH",
        )

    def test_the_capture_raises_the_same_reason(self, tmp_path, monkeypatch, no_prebuilt):
        monkeypatch.setenv("PATH", str(tmp_path))
        monkeypatch.setenv("CC", "no-such-compiler")
        with pytest.raises(tracer.TraceError, match="CC='no-such-compiler' is not on PATH - required to build"):
            tracer.compile_hook(str(tmp_path))


@needs_clang
class TestClangBuildsBoth:
    def test_the_hook_and_spine_with_clang_alone_on_path(self, tmp_path, monkeypatch, no_prebuilt):
        monkeypatch.delenv("CC", raising=False)
        monkeypatch.setenv("PATH", _only(tmp_path, clang=CLANG, ld=shutil.which("ld")))
        build = tmp_path / "build"
        build.mkdir()
        for path in (tracer.compile_hook(str(build)), tracer.compile_spine(str(build))):
            assert open(path, "rb").read(4) == b"\x7fELF", path

    def test_a_prebuilt_wheel_built_with_cc_clang_stamps_clang(self, tmp_path):
        src = tmp_path / "src"
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "prebuilt")
        for name in ("bga", "tools"):
            shutil.copytree(os.path.join(ROOT, name), src / name, ignore=ignore)
        for name in ("pyproject.toml", "setup.py", "README.md"):
            shutil.copy2(os.path.join(ROOT, name), src / name)
        env = {**os.environ, "BGA_HOOK": "prebuilt", "CC": "clang"}
        subprocess.run(
            [sys.executable, "-m", "pip", "wheel", "-q", "--no-deps", "-w", str(tmp_path / "w"), str(src)],
            env=env,
            check=True,
            capture_output=True,
        )
        (wheel,) = (tmp_path / "w").glob("*.whl")
        with zipfile.ZipFile(wheel) as zf:
            stamp = json.loads(zf.read(next(n for n in zf.namelist() if n.endswith("prebuilt/stamp.json"))))
        assert "clang" in stamp["compiler"], stamp


FOREIGN = next(m for m in (183, 62) if m != native_prebuilt.ELF_MACHINE.get(os.uname().machine))


def _foreign_cc(tmp_path):
    """A `$CC` that exits 0 having written an ELF for another machine, as a cross compiler does."""
    script = tmp_path / "cross-cc"
    header = b"\x7fELF\x02\x01" + bytes(12) + FOREIGN.to_bytes(2, "little")
    script.write_text(
        f"#!{sys.executable}\nimport sys\n"
        f"if '--version' in sys.argv: print('cross-cc 1.0'); sys.exit(0)\n"
        f"open(sys.argv[sys.argv.index('-o') + 1], 'wb').write({header!r})\n"
    )
    script.chmod(0o755)
    return str(script)


class TestACrossCompilerCannotCertifyThisHost:
    """Codex on ba5a112e: a cross `$CC` exits 0, so the stamp's machine must come from the binary."""

    def test_the_build_refuses_a_foreign_target(self, tmp_path):
        with pytest.raises(RuntimeError, match=f"for ELF machine {FOREIGN}, not this {os.uname().machine} host"):
            native_prebuilt.build(str(tmp_path / "out"), [_foreign_cc(tmp_path)])
        assert not (tmp_path / "out" / native_prebuilt.STAMP).exists()

    def test_find_refuses_a_foreign_binary_under_a_host_stamp(self, tmp_path, monkeypatch):
        dest = tmp_path / "prebuilt"
        dest.mkdir()
        (dest / "hook.so").write_bytes(b"\x7fELF\x02\x01" + bytes(12) + FOREIGN.to_bytes(2, "little"))
        sources = {
            src: native_prebuilt.sha256(os.path.join(native_prebuilt.HERE, src)) for src in ("hook.c", "spine.c")
        }
        stamp = {"machine": os.uname().machine, "compiler": "cross-cc 1.0", "sources": sources}
        (dest / native_prebuilt.STAMP).write_text(json.dumps(stamp))
        monkeypatch.setattr(native_prebuilt, "PREBUILT_DIR", str(dest))
        assert native_prebuilt.find("hook.so") is None
