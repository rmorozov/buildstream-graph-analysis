"""UX-914: the examples' sysroot says what it is, on both axes.

Two halves, for the same reason `test_the_staged_make_is_the_pinned_one`
has two. The declaration half runs in a clone: every path
`stage_cpp_toolchain.sh` stages is claimed by exactly one declared
package, on exactly one axis, and the pinned rows are read out of
`nix_store_fetch.PINS` rather than typed twice. The staged half runs
the sysroot's own copies and compares what they report against what
this repository declares - so a staging host whose gcc, glibc,
binutils, cmake or coreutils differ cannot change what the examples
measure without reddening here, which is what `make` alone had
(UX-915) and the other five did not.

The script's two axis arrays are parsed out of it rather than copied,
so widening what the examples stage reddens this by itself.
"""
import os
import pathlib
import re

import pytest

from tools import nix_store_fetch, sysroot_manifest

REPO = pathlib.Path(__file__).resolve().parents[2]
STAGER = REPO / "examples/stage_cpp_toolchain.sh"
SYSROOT = REPO / "examples/05-cmake-cpp-toolchain/files/toolchain"


def _axis_array(name):
    """The absolute paths one `<AXIS>_BINARIES=(...)` array declares.
    `$(gcc -print-prog-name=...)` words are not paths in the text and
    are excluded here the same way they are everywhere else."""
    block = re.search(rf"^{name}=\((.*?)^\)", STAGER.read_text(),
                      re.DOTALL | re.MULTILINE)
    assert block, f"stage_cpp_toolchain.sh no longer declares {name}=(...)"
    return {word for word in block.group(1).split() if word.startswith("/")}


class TestTheDeclarationCoversWhatIsStaged:
    def test_every_staged_path_is_claimed_by_exactly_one_package(self):
        """Both directions. A staged path nobody claims is a component
        this repository does not say the version of; a claimed path
        nothing stages is a stale row, and only the pinned names are
        allowed to be absent from the arrays (the script pins those)."""
        staged = _axis_array("RUNTIME_BINARIES") | _axis_array("TOOLCHAIN_BINARIES")
        claimed = [path for row in sysroot_manifest.components()
                   for path in row["binaries"]]
        pinned = {path for row in sysroot_manifest.components()
                  if row["origin"] == "pinned" for path in row["binaries"]}

        assert sorted(set(claimed)) == sorted(claimed), "a path is claimed twice"
        assert staged - set(claimed) == set(), "staged but undeclared"
        assert set(claimed) - staged == pinned, "declared but not staged"

    def test_each_scripts_axis_agrees_with_the_axis_declared_for_it(self):
        for array, axis in (("RUNTIME_BINARIES", "runtime"),
                            ("TOOLCHAIN_BINARIES", "toolchain")):
            declared = {path for row in sysroot_manifest.components()
                        if row["axis"] == axis for path in row["binaries"]}

            assert _axis_array(array) <= declared, array

    def test_both_axes_are_named_and_neither_is_empty(self):
        rows = sysroot_manifest.components()
        axes = {axis: [row["name"] for row in rows if row["axis"] == axis]
                for axis in sysroot_manifest.AXES}

        assert {row["axis"] for row in rows} == set(sysroot_manifest.AXES)
        assert all(axes.values()), axes

    def test_a_binary_with_no_readable_version_says_why(self):
        """The one honest gap - a binary whose version the sysroot
        cannot state - is recorded rather than left looking checked."""
        for row in sysroot_manifest.components():
            if row.get("unreadable"):
                assert row.get("why"), row["name"]
                assert set(row["unreadable"]) <= set(row["binaries"]), row["name"]
            else:
                assert row["version"], row["name"]

    def test_the_pinned_rows_carry_the_pin_tables_own_versions(self):
        pinned = {row["name"]: row for row in sysroot_manifest.components()
                  if row["origin"] == "pinned"}
        paths = nix_store_fetch.host_arch()["paths"]

        assert set(pinned) == set(paths)
        for name, pin in paths.items():
            assert pinned[name]["version"] == pin["version"].rsplit(" ", 1)[-1]
            assert pinned[name]["axis"] == "runtime", name

    def test_the_default_make_belongs_to_the_44_pin(self):
        """`/usr/bin/make` is in neither axis array (the script pins it),
        so nothing else would notice it losing an owner."""
        owners = [row["name"] for row in sysroot_manifest.components()
                  if "/usr/bin/make" in row["binaries"]]

        assert owners == ["make-4.4"], owners

    def test_every_staged_binary_is_probed_rather_than_a_sibling(self):
        """Read off `probes` itself, not restated from the table. No
        binary rides on a sibling's version: `env` answering for `cat`
        is a proxy, and one name of a package can be the host's while
        the rest are not - the host `make` over the 4.4 pin is exactly
        that shape, and a one-probe-per-package manifest read 4.4.1 for
        it while `/usr/bin/make` was 4.3."""
        probed = {}
        for row, label in sysroot_manifest.probe_labels():
            probed.setdefault(row["name"], set()).add(label)

        for row in sysroot_manifest.components():
            want = set(row["binaries"]) - set(row.get("unreadable", ()))
            if row.get("lib_probe"):
                want.add(row["lib_probe"])

            assert probed.get(row["name"], set()) == want, row["name"]

    def test_the_version_token_rule_reads_all_six_formats(self):
        lines = {
            "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0": "13.3.0",
            "cmake version 3.28.3": "3.28.3",
            "GNU ld (GNU Binutils for Ubuntu) 2.42": "2.42",
            "env (GNU coreutils) 9.4": "9.4",
            "GNU C Library (Ubuntu GLIBC 2.39-0ubuntu8.7) stable release "
            "version 2.39.": "2.39",
            "GNU Make 4.4.1": "4.4.1",
        }

        read = {line: sysroot_manifest.declared_version_token(line)
                for line in lines}

        assert read == lines


#: A `skipif`, not a `pytest.skip` in a helper, for the reason
#: `test_the_staged_make_is_the_pinned_one.py` states: the sysroot is
#: gitignored and `test_a_guard_reads_only_what_a_clone_has` reads the
#: mark to know this clause does not run in a clone.
@pytest.mark.skipif(
    not os.path.isdir(os.path.join(SYSROOT, "usr", "bin")),
    reason="examples/05-cmake-cpp-toolchain's toolchain isn't staged - run stage_cpp_toolchain.sh first",
)
class TestTheStagedSysrootMatchesItsDeclaration:
    def test_no_component_disagrees_with_what_is_declared_for_it(self):
        assert sysroot_manifest.divergences(str(SYSROOT)) == []

    def test_every_probeable_row_really_ran(self):
        """A probe that cannot exec records its own error string, which
        equals no declared version - so this would fail through the
        clause above too. Named separately because the two failures need
        different fixes."""
        measured = sysroot_manifest.measure(str(SYSROOT))

        assert not [name for name, version in measured.items()
                    if "did not run" in version or version.startswith("exit ")], measured
