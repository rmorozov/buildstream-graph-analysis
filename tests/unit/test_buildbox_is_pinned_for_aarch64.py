"""UX-1009: BuildStream 2.8.1's aarch64 install has no `buildbox-casd`
or `buildbox-run` (the wheel bundling both is x86_64-only), and bst
locates each by a bare `PATH` lookup (`_get_host_tool_internal`, read
from the 2.8.1 sdist). `nix_buildbox` stages the pinned closure and
answers where its `bin/` lands, for a caller to prepend to `PATH`.

The staging test needs the network (`cache.nixos.org`) and downloads
~70 MiB, so it is opt-in via `BGA_TEST_NIX_NETWORK=1` rather than run
by default - the shape tests below need neither and run always.
"""
import os

import pytest

from tools import nix_buildbox


class TestThePinIsDeclared:
    def test_x86_64_is_refused_rather_than_pinned(self):
        """x86_64's own BuildStream wheel already bundles both
        binaries; pinning one here would be a second, unused copy."""
        with pytest.raises(SystemExit) as raised:
            nix_buildbox.pin("x86_64")
        assert "x86_64" in str(raised.value)

    def test_an_unrelated_arch_is_refused_too(self):
        with pytest.raises(SystemExit):
            nix_buildbox.pin("riscv64")

    def test_aarch64_names_a_real_store_path(self):
        pin = nix_buildbox.pin("aarch64")

        assert pin["store_path"].startswith("/nix/store/")
        assert pin["store_path"].endswith("-buildbox-" + pin["version"])

    def test_bin_dir_is_under_the_pinned_store_path(self, tmp_path):
        path = nix_buildbox.bin_dir(str(tmp_path), "aarch64")

        assert path == str(tmp_path) + nix_buildbox.pin("aarch64")["store_path"] + "/bin"


@pytest.mark.skipif(not os.environ.get("BGA_TEST_NIX_NETWORK"),
                    reason="downloads the pinned buildbox closure from "
                           "cache.nixos.org - set BGA_TEST_NIX_NETWORK=1")
class TestTheStagedClosure:
    def test_buildbox_casd_and_buildbox_run_are_staged(self, tmp_path):
        path = nix_buildbox.stage(str(tmp_path), "aarch64")

        assert os.path.isfile(os.path.join(path, "buildbox-casd"))
        assert os.path.isfile(os.path.join(path, "buildbox-run"))
