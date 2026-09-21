"""UX-915: the examples' `make` is this repository's pin, not whatever
the staging host installed.

Two halves. The pure one runs anywhere: `unpack_nar` against a NAR this
file encodes itself, the arch refusal, and the digest check. The staged
one reads `examples/05`'s own sysroot and *runs* the `make` in it,
through the interpreter symlink `stage_cpp_toolchain.sh` leaves there -
so what it asserts is the version a sandbox would really exec, not what
the pin table says about itself.
"""
import os
import struct
import subprocess

import pytest

from tools import nix_store_fetch

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYSROOT = os.path.join(REPO, "examples", "05-cmake-cpp-toolchain", "files", "toolchain")


def _nar_str(value):
    raw = value if isinstance(value, bytes) else value.encode("utf-8")
    return struct.pack("<Q", len(raw)) + raw + b"\x00" * (-len(raw) % 8)


def _nar_regular(contents, executable=False):
    node = _nar_str("(") + _nar_str("type") + _nar_str("regular")
    if executable:
        node += _nar_str("executable") + _nar_str("")
    return node + _nar_str("contents") + _nar_str(contents) + _nar_str(")")


class TestTheNarReader:
    def test_a_tree_with_an_executable_and_a_symlink_round_trips(self, tmp_path):
        import lzma
        entry = (_nar_str("entry") + _nar_str("(") + _nar_str("name")
                 + _nar_str("make") + _nar_str("node")
                 + _nar_regular(b"#!/bin/sh\n", executable=True) + _nar_str(")"))
        link = (_nar_str("entry") + _nar_str("(") + _nar_str("name")
                + _nar_str("cc") + _nar_str("node") + _nar_str("(")
                + _nar_str("type") + _nar_str("symlink") + _nar_str("target")
                + _nar_str("make") + _nar_str(")") + _nar_str(")"))
        bin_dir = (_nar_str("(") + _nar_str("type") + _nar_str("directory")
                   + entry + link + _nar_str(")"))
        root = (_nar_str("nix-archive-1") + _nar_str("(") + _nar_str("type")
                + _nar_str("directory") + _nar_str("entry") + _nar_str("(")
                + _nar_str("name") + _nar_str("bin") + _nar_str("node")
                + bin_dir + _nar_str(")") + _nar_str(")"))

        dest = str(tmp_path / "out")
        nix_store_fetch.unpack_nar(lzma.compress(root), dest)

        assert open(os.path.join(dest, "bin", "make"), encoding="utf-8").read() == "#!/bin/sh\n"
        assert os.access(os.path.join(dest, "bin", "make"), os.X_OK)
        assert os.readlink(os.path.join(dest, "bin", "cc")) == "make"


class TestThePinIsVerified:
    def test_an_unpinned_arch_is_refused_rather_than_defaulted(self):
        with pytest.raises(SystemExit) as raised:
            nix_store_fetch.host_arch("s390x")
        assert "s390x" in str(raised.value)

    def test_a_digest_that_disagrees_with_the_pin_is_an_error(self, tmp_path):
        source = tmp_path / "some.nar.xz"
        source.write_bytes(b"not the pinned bytes")

        with pytest.raises(ValueError) as raised:
            nix_store_fetch.fetch(source.as_uri(), "00" * 32, str(tmp_path / "cache"))
        assert "00" * 32 in str(raised.value)

    def test_every_pin_names_its_own_version_in_its_store_path(self):
        for group in nix_store_fetch.PINS.values():
            for name, pin in group["paths"].items():
                version = pin["version"].rsplit(" ", 1)[-1]
                assert pin["store_path"].endswith(f"-gnumake-{version}"), name


#: A `skipif`, not a `pytest.skip` in a helper: the sysroot is
#: gitignored, so `test_a_guard_reads_only_what_a_clone_has` reads the
#: mark to know these two clauses do not run in a clone.
@pytest.mark.skipif(
    not os.path.isdir(os.path.join(SYSROOT, "usr", "bin")),
    reason="examples/05-cmake-cpp-toolchain's toolchain isn't staged - run stage_cpp_toolchain.sh first",
)
class TestTheStagedMake:
    def test_usr_bin_make_resolves_into_the_pinned_store_path(self):
        group = nix_store_fetch.host_arch()
        pin = group["paths"]["make-4.4"]

        target = os.readlink(os.path.join(SYSROOT, "usr", "bin", "make"))

        assert target.endswith(pin["store_path"] + "/bin/make"), target

    def test_the_staged_make_reports_the_pinned_version(self):
        group = nix_store_fetch.host_arch()
        pin = group["paths"]["make-4.4"]
        loader = os.path.join(SYSROOT + group["interpreter_dir"], group["loader"])

        result = subprocess.run(
            [loader, os.path.join(SYSROOT, "usr", "bin", "make"), "--version"],
            capture_output=True, text=True, timeout=30)

        assert result.returncode == 0, result.stderr
        assert result.stdout.splitlines()[0] == pin["version"], result.stdout
