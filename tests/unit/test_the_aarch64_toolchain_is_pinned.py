"""UX-1009: the Graviton runner CodSpeed offers is aarch64, and the
`x86_64`-only pin tables refused it outright. This guards the shape of
the new `aarch64` groups (same fields, same store-path/version
agreement the x86_64 groups already carry) and that
`stage_cpp_toolchain.sh` reads the loader name from the pin rather
than naming `ld-linux-x86-64.so.2` itself - so an arch switch does not
need a second hardcode fixed alongside it.

No network and no aarch64 host needed: everything here is table shape
and script text, the same class of guard the existing x86_64 pin tests
already run unconditionally.
"""
import pathlib
import re

import pytest

from tools import nix_store_fetch, nix_toolchain

REPO = pathlib.Path(__file__).resolve().parents[2]
STAGER = REPO / "examples/stage_cpp_toolchain.sh"
STORE_PATH = re.compile(r"^/nix/store/[0-9a-df-np-sv-z]{32}-[\w.+-]+$")


class TestTheStoreFetchAarch64Group:
    def test_aarch64_is_no_longer_refused(self):
        group = nix_store_fetch.host_arch("aarch64")

        assert group["loader"] == "ld-linux-aarch64.so.1"

    def test_its_interpreter_dir_names_the_aarch64_glibc(self):
        group = nix_store_fetch.host_arch("aarch64")

        assert group["interpreter_dir"].endswith("-glibc-2.40-224/lib")
        assert group["interpreter_dir"] != nix_store_fetch.host_arch("x86_64")[
            "interpreter_dir"]

    def test_an_unrelated_arch_is_still_refused(self):
        """The refusal `nix_store_fetch.host_arch`'s docstring names -
        adding aarch64 must not turn it into a fallback."""
        with pytest.raises(SystemExit):
            nix_store_fetch.host_arch("riscv64")


class TestTheToolchainAarch64Group:
    def test_the_same_three_packages_are_pinned(self):
        assert set(nix_toolchain.pins("aarch64")) == set(
            nix_toolchain.pins("x86_64"))

    def test_each_root_is_a_store_path_carrying_its_declared_version(self):
        for name, pin in nix_toolchain.pins("aarch64").items():
            assert STORE_PATH.match(pin["store_path"]), name
            assert pin["store_path"].endswith("-" + pin["version"]), name
            assert pin["axis"] == "toolchain", name

    def test_the_versions_match_the_x86_64_pins(self):
        """Same channel, same versions - only the store path (and the
        glibc it was built against) differs per arch."""
        aarch64 = nix_toolchain.pins("aarch64")
        x86_64 = nix_toolchain.pins("x86_64")

        assert {n: p["version"] for n, p in aarch64.items()} == {
            n: p["version"] for n, p in x86_64.items()}
        assert {p["store_path"] for p in aarch64.values()} != {
            p["store_path"] for p in x86_64.values()}


class TestTheStagerReadsTheLoaderFromThePin:
    def test_no_pinned_loader_lookup_hardcodes_x86_64(self):
        """The two spots that used to read the pinned toolchain's own
        interpreter (as opposed to the RUNTIME axis' host loader,
        staged from a fixed short list further up) go through
        `--loader` now, so they follow whichever arch's pin is staged."""
        text = STAGER.read_text()

        assert "$PINNED_LOADER" in text
        pinned_lookups = [line for line in text.splitlines()
                          if "INTERPRETER_DIR" in line and "ld-linux" in line]
        assert pinned_lookups == []

    def test_the_loader_flag_answers_the_pinned_groups_own_name(self, capsys):
        assert nix_store_fetch.main(
            ["unused", "--arch", "aarch64", "--loader"]) == 0
        assert capsys.readouterr().out.strip() == "ld-linux-aarch64.so.1"
