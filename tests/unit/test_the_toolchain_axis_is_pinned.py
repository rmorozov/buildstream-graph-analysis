"""UX-925: the examples' compiler is this repository's, not the host's.

`UX-914` declared the toolchain axis and left it a host fact. This
reads that it is a pin: three store paths named here, staged as one
closure at their own `/nix/store/<hash>` prefixes with their
content-addresses intact, reached through the `-B` and `--sysroot`
that `UX-930` learned to read back.

The half that needs a staged sysroot is skipped in a clone, the way
`test_the_staged_make_is_the_pinned_one` skips - the tree is
gitignored. The mutations run in a hardlink clone of it (0.13s, no
real disk), never in the tree itself: `make test` is not read-only and
a guard's write escapes into the repository.

What a mixture would look like is checked as its own clause. A host
`gcc`, its own internal tree, or `/usr/include` staged beside the pin
links and means nothing, and only the read-back notices.
"""
import os
import pathlib
import re
import shutil
import subprocess

import pytest

from tools import nix_closure, nix_toolchain, sysroot_manifest
from tools import toolchain_params as tp

REPO = pathlib.Path(__file__).resolve().parents[2]
STAGER = REPO / "examples/stage_cpp_toolchain.sh"
SYSROOT = REPO / "examples/05-cmake-cpp-toolchain/files/toolchain"
STORE_PATH = re.compile(r"^/nix/store/[0-9a-df-np-sv-z]{32}-[\w.+-]+$")

#: The runtime axis as `UX-914` left it, written out rather than read
#: from the table it is checking. `UX-925`'s last claim is that the two
#: axes are independent, and a copy of the table would agree with any
#: change to it.
RUNTIME_ROWS = {
    ("glibc", "host", "2.39"),
    ("coreutils", "host", "9.4"),
    ("dash", "host", None),
    ("make-4.2", "pinned", "4.2.1"),
    ("make-4.4", "pinned", "4.4.1"),
}

staged_only = pytest.mark.skipif(
    not os.path.isdir(os.path.join(SYSROOT, "nix", "store")),
    reason="examples/05-cmake-cpp-toolchain's toolchain isn't staged - run stage_cpp_toolchain.sh first",
)


@pytest.fixture
def clone(tmp_path):
    """The staged tree, hardlinked. Every mutation below works on this."""
    dest = tmp_path / "sysroot"
    subprocess.run(["cp", "-al", str(SYSROOT), str(dest)], check=True)
    return str(dest)


def _replace(path, contents=None, source=None):
    """Overwrite one file **in the clone only**. The clone is
    hardlinks, so writing through one of them edits the tree the
    examples build from - which is how this file corrupted its own
    sysroot the first time it ran. Unlink first: that drops this
    name's link and leaves the original inode alone."""
    path = pathlib.Path(path)
    mode = path.stat().st_mode
    path.unlink()
    if source is not None:
        shutil.copy2(source, path)
    else:
        path.write_text(contents)
    path.chmod(mode)


class TestThePinIsDeclared:

    def test_each_root_is_a_store_path_carrying_its_declared_version(self):
        """The name is not what identifies a store path - the channel
        carries four `gcc-14.3.0` paths, one per architecture, and
        `UX-915` pinned the wrong one that way. But a pin whose *name*
        disagrees with the version declared beside it is a typo, and
        nothing else here would read it."""
        for name, pin in nix_toolchain.pins().items():
            assert STORE_PATH.match(pin["store_path"]), name
            assert pin["store_path"].endswith("-" + pin["version"]), name
            assert pin["axis"] == "toolchain", name

    def test_no_two_packages_claim_the_same_binary(self):
        claimed = [path for pin in nix_toolchain.pins().values()
                   for path in pin["binaries"]]

        assert sorted(set(claimed)) == sorted(claimed)

    def test_an_unpinned_architecture_is_refused_rather_than_guessed(self):
        """`nix_store_fetch.host_arch`'s rule, one table over: a
        wrong-arch compiler is not a degraded example, it is a sandbox
        whose every compile fails to exec."""
        with pytest.raises(SystemExit):
            nix_toolchain.pins("sparc64")

    def test_the_stager_stages_no_host_toolchain_binary(self):
        """Read out of the script's own axis array, so putting one back
        reddens here rather than quietly shipping a host compiler."""
        block = re.search(r"^TOOLCHAIN_BINARIES=\((.*?)^\)", STAGER.read_text(),
                          re.DOTALL | re.MULTILINE)

        assert block, "stage_cpp_toolchain.sh no longer declares the array"
        assert [word for word in block.group(1).split()
                if word.startswith("/")] == []


class TestTheFiveParametersAreDerivedFromTheClosure:

    def test_a_tree_with_no_pinned_gcc_is_not_read_as_pinned(self, tmp_path):
        """A `/nix/store` under the tree is not a pinned toolchain -
        the `make` pins put one there. The declared root decides, and
        reading a half-empty store as pinned would write a `-B` at
        nothing, which is this row's own silent case."""
        (tmp_path / "nix/store/aaa-something/lib").mkdir(parents=True)
        (tmp_path / "nix/store/aaa-something/lib/crt1.o").touch()

        assert nix_toolchain.prefixes(str(tmp_path)) is None
        assert not tp.is_pinned(str(tmp_path))

    @staticmethod
    def _skeleton(root, pins):
        """The five mark files, under the declared store paths."""
        for path in (pins["gcc"]["store_path"]
                     + "/libexec/gcc/x86_64-unknown-linux-gnu/14.3.0/cc1",
                     pins["gcc"]["store_path"]
                     + "/lib/gcc/x86_64-unknown-linux-gnu/14.3.0/libgcc.a",
                     "/nix/store/bbb-gcc-14.3.0-lib/lib/libstdc++.so",
                     pins["binutils"]["store_path"] + "/bin/ld.bfd",
                     "/nix/store/ccc-glibc-2.40-224/lib/crt1.o"):
            made = pathlib.Path(root + path)
            made.parent.mkdir(parents=True, exist_ok=True)
            made.touch()

    def test_all_five_are_found_by_a_mark_no_other_path_has(self, tmp_path):
        pins = nix_toolchain.pins()
        self._skeleton(str(tmp_path), pins)

        found = nix_toolchain.prefixes(str(tmp_path))

        assert sorted(found) == sorted(row["name"]
                                       for row in nix_toolchain.PREFIXES)
        assert all(path is not None and path.startswith(str(tmp_path))
                   for path in found.values()), found

    def test_a_prefix_whose_mark_is_gone_is_none_and_never_empty(self, tmp_path):
        """The mutation. `-B` at a directory holding no `as` falls back
        to `PATH` and prints nothing, so a prefix that cannot be
        located is left out of the flags rather than written at the
        tree root."""
        pins = nix_toolchain.pins()
        self._skeleton(str(tmp_path), pins)
        os.unlink(str(tmp_path) + pins["binutils"]["store_path"] + "/bin/ld.bfd")

        found = nix_toolchain.prefixes(str(tmp_path))
        flags = tp.flags_for(tp.parameters(str(tmp_path)))

        assert found["binutils"] is None
        assert not [flag for flag in flags if flag == "-B"], flags
        assert len([flag for flag in flags if flag.startswith("-B")]) == 4

    def test_and_a_shim_is_refused_while_one_is_missing(self, tmp_path, capsys):
        pins = nix_toolchain.pins()
        self._skeleton(str(tmp_path), pins)
        os.unlink(str(tmp_path) + pins["binutils"]["store_path"] + "/bin/ld.bfd")

        exit_code = tp.main([str(tmp_path), "--shim", "gcc"])

        assert exit_code == 1
        assert "binutils" in capsys.readouterr().err

    def test_the_shims_flags_name_the_sandbox_not_the_staging_tree(self,
                                                                   tmp_path):
        """The shim is written on the staging host and read inside the
        sandbox, where the staged tree *is* `/`. A shim carrying the
        staging tree's own absolute paths names nothing there, and
        every one of those parameters is silent when it is wrong."""
        pins = nix_toolchain.pins()
        self._skeleton(str(tmp_path), pins)
        params = tp.parameters(str(tmp_path))

        text = tp.shim_text(nix_toolchain.driver_target("/", "gcc"),
                            tp.reroot(params, "/"))

        assert str(tmp_path) not in text, text
        assert text.count("-B/nix/store/") == 5
        assert "'--sysroot=/'" in text


@staged_only
class TestTheStagedTreeCarriesThePinAndNothingElse:

    def test_every_toolchain_version_is_the_one_declared(self):
        assert sysroot_manifest.divergences(str(SYSROOT)) == []

    def test_every_file_class_answers_from_the_half_it_declares(self):
        assert tp.is_pinned(str(SYSROOT))
        assert tp.divergences(str(SYSROOT)) == []

    def test_the_cxx_headers_are_the_compilers_own_now(self):
        """The one word `UX-925` flips. On Ubuntu they are their own
        package under `/usr/include`; the pin carries them inside its
        store prefix, so no `--sysroot` has to reach them."""
        path, owner = tp.measure(str(SYSROOT))["cxx-headers"]

        assert owner == tp.TOOLCHAIN
        assert "/include/c++/" in path

    def test_the_closure_names_no_store_path_the_tree_lacks(self):
        """`UX-927`'s assertion on the real tree: a reference staged
        nowhere is one the staging host answered."""
        assert nix_closure.dangling_store_refs(str(SYSROOT)) == []

    def test_no_host_toolchain_file_is_staged_beside_the_pin(self):
        """The mixture clause. Each of these is a path the host
        compiler reached and the pin does not, and a build that found
        both would link and mean nothing."""
        for absent in ("usr/include", "usr/lib/gcc", "usr/libexec/gcc",
                       "usr/lib/x86_64-linux-gnu/crt1.o",
                       "usr/share/cmake-3.28"):
            assert not (SYSROOT / absent).exists(), absent

    def test_each_driver_is_a_shim_that_execs_the_pins_own_binary(self):
        for name, execs in sorted(nix_toolchain.DRIVERS.items()):
            text = (SYSROOT / "usr/bin" / name).read_text()

            assert text.startswith("#!/bin/sh\n"), name
            assert "exec '/nix/store/" in text, name
            assert text.split("exec '")[1].startswith(
                nix_toolchain.pins()["gcc"]["store_path"] + "/bin/" + execs), name

    def test_each_other_pinned_binary_is_a_link_into_its_store_path(self):
        for package, pin in sorted(nix_toolchain.pins().items()):
            for path in pin["binaries"]:
                name = os.path.basename(path)
                if name in nix_toolchain.DRIVERS:
                    continue
                link = SYSROOT / path.lstrip("/")

                assert link.is_symlink(), path
                assert not os.readlink(link).startswith("/"), \
                    f"{path} is absolute, so it dangles on the staging host"
                assert os.path.realpath(link).startswith(
                    str(SYSROOT) + pin["store_path"]), (package, path)


@staged_only
class TestAHostToolchainStagedOverThePinReddens:
    """The mutation `UX-914` ran against the `make` pin, applied to the
    pinned tree - and the one `UX-925`'s acceptance test names. Each
    runs in a hardlink clone, so nothing here touches the tree the
    examples build from."""

    def test_a_host_gcc_over_the_shim_is_read_off_the_shim(self, clone):
        """The version probes cannot catch this one and do not pretend
        to: they ask the pin's own binary, because a shim is a shell
        script whose `/nix/store` flags resolve only in the sandbox. So
        the shim is read as a file instead, by the stager and here."""
        host = shutil.which("gcc")
        if host is None:
            pytest.skip("no host gcc to stage over the pin")
        _replace(os.path.join(clone, "usr/bin/gcc"),
                 source=os.path.realpath(host))

        assert [name for name, _target
                in nix_toolchain.shim_divergences(clone)] == ["gcc"]
        assert nix_toolchain.main([clone, "--check-shims"]) == 1

    def test_a_shim_pointed_at_the_host_driver_is_read_too(self, clone):
        """The quieter half: still a shim, still shell-only, still
        every flag in place - and one word of its `exec` line changed."""
        shim = os.path.join(clone, "usr/bin/g++")
        text = pathlib.Path(shim).read_text()
        _replace(shim, contents=text.replace(
            "exec '" + nix_toolchain.pins()["gcc"]["store_path"], "exec '/usr"))

        assert [name for name, _target
                in nix_toolchain.shim_divergences(clone)] == ["g++"]

    def test_a_host_helper_over_the_pins_is_read_too(self, clone):
        """`cc1plus` is not on `PATH` and no element names it, so
        nothing but a probe of its own would notice."""
        pinned = sysroot_manifest.helper_path(clone, "cc1plus")
        host = subprocess.run(["gcc", "-print-prog-name=cc1plus"],
                              capture_output=True, text=True).stdout.strip()
        if not os.path.isabs(host):
            pytest.skip("this host resolves no cc1plus to stage over the pin")
        _replace(pinned, source=host)

        assert "cc1plus" in [row[1]
                             for row in sysroot_manifest.divergences(clone)]

    def test_a_closure_whose_binutils_is_gone_stops_answering(self, clone):
        """Not `-B` at an empty directory - `-B` at a directory that is
        not there at all, which gcc also takes without a word."""
        shutil.rmtree(clone + nix_toolchain.pins()["binutils"]["store_path"])

        assert tp.measure(clone)["assembler"] == (None, None)
        assert "assembler" in [row[0] for row in tp.divergences(clone)]


@staged_only
class TestTheRuntimeAxisDidNotMove:

    def test_its_rows_are_what_UX_914_left(self):
        rows = {(row["name"], row["origin"], row["version"])
                for row in sysroot_manifest.components()
                if row["axis"] == "runtime"}

        assert rows == RUNTIME_ROWS

    def test_the_staged_shell_and_coreutils_are_still_the_hosts(self):
        measured = sysroot_manifest.measure(str(SYSROOT))

        assert measured["/usr/bin/env"] == "9.4"
        assert measured["libc.so.6"] == "2.39"

    def test_the_target_glibc_is_not_the_closures(self):
        """Two glibcs in one tree, and the reason both are declared:
        the host-staged 2.39 loads the tree's own `sh` and coreutils,
        and the closure's 2.40 loads the pin and everything the pin
        links. Reading one for the other is how a runtime row would
        move without anything saying so."""
        target = os.path.realpath(sysroot_manifest.nix_store_fetch.sysroot_lib_dir(
            str(SYSROOT), sysroot_manifest.nix_store_fetch.host_arch()))
        closure = nix_toolchain.glibc_store_path(str(SYSROOT))

        assert closure is not None
        assert not target.startswith(os.path.realpath(closure))
