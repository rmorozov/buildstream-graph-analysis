#!/usr/bin/env python3
"""UX-1009: `buildbox-casd`/`buildbox-run` for a host BuildStream 2.8.1's
own wheel does not carry one for.

PyPI publishes six `manylinux_2_28_x86_64` wheels for 2.8.1 plus the
sdist; aarch64 pip builds from the sdist, which bundles neither binary.
Both are located the same way regardless (`utils._get_host_tool_internal`
in `_cas/casdprocessmanager.py` and `sandbox/_sandboxbuildboxrun.py`,
read from the downloaded sdist 2026-09-24): a bare `PATH` lookup, no
sysroot involved, so there is nothing for `nix_toolchain`'s `-B`/shim
machinery to do here - staging the pin's own `bin/` onto `PATH` is the
whole fix.

A pinned root, not `nix_closure --root` typed straight into the
workflow: the store path is then declared and tested exactly like
`nix_toolchain.TOOLCHAIN_PINS`, rather than living only as a CI YAML
string no unit test reads.
"""
import argparse
import os
import platform
import sys

from tools import nix_closure

#: `References` on this store path all reach the same aarch64 glibc
#: `nix_store_fetch`/`nix_toolchain` pin (UX-1009). x86_64 is not
#: pinned here: its BuildStream wheel bundles both binaries already.
BUILDBOX_PINS = {
    "aarch64": {
        "version": "1.4.7",
        "store_path": ("/nix/store/adhcidhjjrgih5hhfqcnddi5pz1flcsz"
                       "-buildbox-1.4.7"),
    },
}


def pin(arch=None) -> dict:
    """This machine's pinned buildbox, or a refusal - never another
    arch's, for `nix_store_fetch.host_arch`'s reason."""
    arch = arch or platform.machine()
    if arch not in BUILDBOX_PINS:
        raise SystemExit(
            f"nix_buildbox: no pinned buildbox for {arch!r} "
            f"(pinned: {', '.join(sorted(BUILDBOX_PINS))}) - x86_64's "
            f"BuildStream wheel bundles its own (UX-1009)")
    return BUILDBOX_PINS[arch]


def bin_dir(dest: str, arch=None) -> str:
    """Where the pin's own `buildbox-casd`/`buildbox-run` land under
    `dest`, for the caller to prepend to `PATH`."""
    return dest.rstrip("/") + pin(arch)["store_path"] + "/bin"


def stage(dest: str, arch=None, cache_dir=None) -> str:
    """The pinned closure under `dest`; only `/` runs (absolute interp)."""
    nix_closure.stage_closure(
        dest, [pin(arch)["store_path"]],
        cache_dir or nix_closure.default_cache_dir())
    return bin_dir(dest, arch)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("dest", help="the sysroot root to stage under")
    parser.add_argument("--arch", default=None)
    parser.add_argument("--cache-dir", default=None)
    args = parser.parse_args(argv)
    path = stage(args.dest, args.arch, args.cache_dir)
    if not os.path.isdir(path):
        raise SystemExit(f"nix_buildbox: staged, but {path} is missing")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
