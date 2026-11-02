"""UX-1373: `BGA_HOOK=prebuilt` ships the hook and spine compiled; the default wheel compiles them at capture."""

import json
import os
import shutil
import subprocess
import sys
import zipfile

import pytest

from tools import bga_doctor
from tools import bst_native_build_tracer as tracer
from tools.native_trace import prebuilt as native_prebuilt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CC = shutil.which("cc") or shutil.which("gcc")
needs_cc = pytest.mark.skipif(CC is None, reason="no C compiler on PATH")
PREBUILT_FILES = {"hook.so", "spine", "stamp.json"}


def elf(name):
    """A stand-in binary: this host's ELF header (machine, class, byte order), then its name."""
    machine, cls, data = native_prebuilt.ELF_TARGET[os.uname().machine]
    order = "little" if data == 1 else "big"
    return b"\x7fELF" + bytes([cls, data]) + bytes(12) + machine.to_bytes(2, order) + b"prebuilt " + name.encode()


@pytest.fixture
def stamped(tmp_path, monkeypatch):
    """A prebuilt directory whose stamp matches this checkout's sources, with stand-in binaries."""
    dest = tmp_path / "prebuilt"
    dest.mkdir()
    for name in ("hook.so", "spine"):
        (dest / name).write_bytes(elf(name))
    stamp = {
        "machine": os.uname().machine,
        "compiler": "cc (stand-in) 1.0",
        "sources": {
            src: native_prebuilt.sha256(os.path.join(native_prebuilt.HERE, src)) for src in ("hook.c", "spine.c")
        },
    }
    (dest / "stamp.json").write_text(json.dumps(stamp))
    monkeypatch.setattr(native_prebuilt, "PREBUILT_DIR", str(dest))
    return dest, stamp


def _restamp(dest, stamp, **changes):
    (dest / "stamp.json").write_text(json.dumps({**stamp, **changes}))


class TestAPrebuiltBinaryIsUsedOnlyWhileItMatches:
    def test_a_matching_stamp_finds_both(self, stamped):
        dest, _ = stamped
        assert native_prebuilt.find("hook.so") == str(dest / "hook.so")
        assert native_prebuilt.find("spine") == str(dest / "spine")

    def test_no_prebuilt_directory_finds_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(native_prebuilt, "PREBUILT_DIR", str(tmp_path / "absent"))
        assert native_prebuilt.find("hook.so") is None

    def test_a_source_changed_since_the_build_is_stale(self, stamped):
        dest, stamp = stamped
        _restamp(dest, stamp, sources={**stamp["sources"], "hook.c": "0" * 64})
        assert native_prebuilt.find("hook.so") is None
        assert native_prebuilt.find("spine") == str(dest / "spine")

    def test_another_machine_s_binary_is_not_used(self, stamped):
        dest, stamp = stamped
        _restamp(dest, stamp, machine="not-" + stamp["machine"])
        assert native_prebuilt.find("hook.so") is None

    def test_a_stamp_without_its_binary_finds_nothing(self, stamped):
        dest, _ = stamped
        (dest / "spine").unlink()
        assert native_prebuilt.find("spine") is None


class TestTheCaptureTakesThePrebuiltWithNoCompiler:
    def test_hook_and_spine_are_copied_with_an_empty_path(self, stamped, tmp_path, monkeypatch):
        monkeypatch.setenv("PATH", str(tmp_path / "empty"))
        build = tmp_path / "build"
        build.mkdir()
        assert open(tracer.compile_hook(str(build)), "rb").read() == elf("hook.so")
        assert open(tracer.compile_spine(str(build)), "rb").read() == elf("spine")

    def test_a_stale_hook_with_no_compiler_fails_as_before(self, stamped, tmp_path, monkeypatch):
        dest, stamp = stamped
        _restamp(dest, stamp, sources={**stamp["sources"], "hook.c": "0" * 64})
        monkeypatch.setenv("PATH", str(tmp_path / "empty"))
        with pytest.raises(tracer.TraceError, match="no C compiler"):
            tracer.compile_hook(str(tmp_path))

    @needs_cc
    def test_a_stale_hook_is_compiled_fresh(self, stamped, tmp_path):
        dest, stamp = stamped
        _restamp(dest, stamp, sources={**stamp["sources"], "hook.c": "0" * 64})
        hook = tracer.compile_hook(str(tmp_path))
        assert open(hook, "rb").read(4) == b"\x7fELF"

    def test_doctor_needs_no_compiler_while_both_match(self, stamped, tmp_path, monkeypatch):
        monkeypatch.setenv("PATH", str(tmp_path / "empty"))
        check = bga_doctor.check_compiler()
        assert check["status"] == bga_doctor.OK, check
        assert "cc (stand-in) 1.0" in check["summary"]

    def test_doctor_fails_without_a_compiler_once_one_is_stale(self, stamped, tmp_path, monkeypatch):
        dest, stamp = stamped
        _restamp(dest, stamp, sources={**stamp["sources"], "spine.c": "0" * 64})
        monkeypatch.setenv("PATH", str(tmp_path / "empty"))
        assert bga_doctor.check_compiler()["status"] == bga_doctor.FAIL


def _tree(tmp_path):
    """The files a wheel build reads, copied out so its build/ never touches the checkout."""
    src = tmp_path / "src"
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "prebuilt")
    for name in ("bga", "tools"):
        shutil.copytree(os.path.join(ROOT, name), src / name, ignore=ignore)
    for name in ("pyproject.toml", "setup.py", "README.md"):
        shutil.copy2(os.path.join(ROOT, name), src / name)
    return src


def _wheel(src, out, mode):
    env = {**os.environ, "BGA_HOOK": mode}
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "-q", "--no-deps", "-w", str(out), str(src)],
        env=env,
        check=True,
        capture_output=True,
    )
    (wheel,) = out.glob("*.whl")
    return wheel


def _prebuilt_entries(wheel):
    with zipfile.ZipFile(wheel) as zf:
        return {n.rsplit("/", 1)[1]: zf.getinfo(n) for n in zf.namelist() if "/native_trace/prebuilt/" in n}


@pytest.fixture(scope="module")
def tree(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("wheels")
    return tmp, _tree(tmp)


@pytest.fixture(scope="module")
def wheels(tree):
    tmp, src = tree
    return _wheel(src, tmp / "pre", "prebuilt"), _wheel(src, tmp / "source", "source")


@needs_cc
class TestBothWheelKindsBuild:
    """Built in one tree, prebuilt first: the source wheel after it must not inherit build/'s binaries."""

    def test_an_unknown_kind_is_refused(self, tree):
        tmp, src = tree
        with pytest.raises(subprocess.CalledProcessError) as raised:
            _wheel(src, tmp / "bogus", "bogus")
        assert b"BGA_HOOK='bogus': expected one of source, prebuilt" in raised.value.stderr

    def test_the_prebuilt_wheel_is_tagged_for_this_machine_and_no_python_abi(self, wheels):
        assert wheels[0].name.endswith(f"-py3-none-linux_{os.uname().machine}.whl"), wheels[0].name

    def test_the_prebuilt_wheel_carries_both_binaries_and_their_stamp(self, wheels):
        entries = _prebuilt_entries(wheels[0])
        assert set(entries) == PREBUILT_FILES
        for name in ("hook.so", "spine"):
            assert entries[name].external_attr >> 16 & 0o111, f"{name} lost its executable bit"

    def test_the_stamp_names_the_sources_shipped_beside_it(self, wheels):
        with zipfile.ZipFile(wheels[0]) as zf:
            stamp = json.loads(zf.read(next(n for n in zf.namelist() if n.endswith("prebuilt/stamp.json"))))
        for src in ("hook.c", "spine.c"):
            assert stamp["sources"][src] == native_prebuilt.sha256(os.path.join(native_prebuilt.HERE, src))

    def test_the_source_wheel_is_pure_and_carries_no_binary(self, wheels):
        assert wheels[1].name.endswith("-py3-none-any.whl"), wheels[1].name
        assert _prebuilt_entries(wheels[1]) == {}
