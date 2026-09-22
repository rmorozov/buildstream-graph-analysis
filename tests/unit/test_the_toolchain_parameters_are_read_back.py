"""UX-930: `-B` and `--sysroot` are read back, not assumed.

Every one of gcc's path parameters falls back to a host absolute path
when the parameterized location is empty, and none of them says so:
`-B <empty> -print-prog-name=cc1` reports the compiled-in prefix and
exits 0. So the guard here is the same one `UX-914` applies to the
sysroot's versions, applied to its search paths - ask the driver where
each file class actually came from, and red when the answer is outside
the staged tree.

The fixture is a miniature sysroot, hardlink-cloned off this host the
way `stage_cpp_toolchain.sh` clones its own output - 65ms and no real
disk where `/usr` and the temporary directory share a filesystem, a
1.6s copy where they do not. Not symlinked: a symlinked include
directory makes `--sysroot` skip it and `-H` report the host's path,
so the fixture would answer a question the real sysroot never asks.
"""
import os
import pathlib
import re
import shutil
import subprocess

import pytest

from tools import toolchain_params as tp

REPO = pathlib.Path(__file__).resolve().parents[2]
STAGER = REPO / "examples/stage_cpp_toolchain.sh"
HOST_HEADERS = pathlib.Path("/usr/include")
#: One wording for every clause in this file, module-level so the skip
#: census can read it without running (`test_every_skip_reason_is_declared`).
NO_TOOLCHAIN = "no host toolchain to clone a sysroot off"

# The fixture is cloned off this host's own toolchain, so in a clone
# with no compiler installed there is nothing to read and the file
# skips rather than failing (UX-213's rule).
pytestmark = pytest.mark.skipif(
    not HOST_HEADERS.exists() or shutil.which("gcc") is None,
    reason=NO_TOOLCHAIN)


def _ask_host(*argv):
    result = subprocess.run(["gcc", *argv], capture_output=True, text=True,
                            timeout=60)
    return result.stdout.strip()


def _clone(real: pathlib.Path, dest: pathlib.Path) -> None:
    """`cp -al` where it works, `cp -a` where the two trees are on
    different filesystems.

    The `rmtree` between the attempts is the whole of it. A
    cross-device `cp -al` **creates the destination directory** and
    only then fails per file (`Invalid cross-device link`, exit 1), so
    a plain retry copies *into* what it left behind and nests the tree
    one level down - every glob then misses and the file reads as a
    host with no toolchain. Run 35734149048, where the runner's `/usr`
    and its temporary directory are on different filesystems.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    for flags in ("-al", "-a"):
        if dest.exists():
            shutil.rmtree(dest)
        done = subprocess.run(["cp", flags, str(real), str(dest)],
                              capture_output=True, text=True)
        if done.returncode == 0:
            return
    pytest.skip(NO_TOOLCHAIN)


@pytest.fixture(scope="module")
def mini(tmp_path_factory):
    """A sysroot shaped like the stager's."""
    cc1 = pathlib.Path(_ask_host("-print-prog-name=cc1"))
    libgcc = pathlib.Path(_ask_host("-print-file-name=libgcc.a"))
    crt1 = pathlib.Path(os.path.normpath(_ask_host("-print-file-name=crt1.o")))
    if not (cc1.is_absolute() and libgcc.is_absolute() and crt1.exists()):
        pytest.skip(NO_TOOLCHAIN)
    dest = tmp_path_factory.mktemp("mini")
    (dest / "usr/bin").mkdir(parents=True)
    for name in ("gcc", "g++"):
        found = shutil.which(name)
        if found is None:
            pytest.skip(NO_TOOLCHAIN)
        shutil.copy2(os.path.realpath(found), dest / "usr/bin" / name)
    for real in (cc1.parent, libgcc.parent, crt1.parent,
                 HOST_HEADERS):
        _clone(real, dest / str(real).lstrip("/"))
    # The clone is the fixture's one claim, so it is checked here
    # rather than left to surface as seven unrelated-looking failures
    # about a host that has a toolchain.
    for marker in (cc1, libgcc, crt1):
        landed = dest / str(marker).lstrip("/")
        assert landed.exists(), f"the clone did not land {marker} at {landed}"
    return str(dest)


@pytest.fixture(scope="module")
def mini_symlinked(tmp_path_factory):
    """The same shape with its big trees symlinked rather than cloned -
    the one fixture where the header probe's answer and the header's
    own `realpath` differ."""
    cc1 = pathlib.Path(_ask_host("-print-prog-name=cc1"))
    libgcc = pathlib.Path(_ask_host("-print-file-name=libgcc.a"))
    if not (cc1.is_absolute() and libgcc.is_absolute()):
        pytest.skip(NO_TOOLCHAIN)
    dest = tmp_path_factory.mktemp("mini-symlinked")
    (dest / "usr/bin").mkdir(parents=True)
    found = shutil.which("gcc")
    if found is None:
        pytest.skip(NO_TOOLCHAIN)
    shutil.copy2(os.path.realpath(found), dest / "usr/bin/gcc")
    for real in (cc1.parent, libgcc.parent):
        link = dest / str(real).lstrip("/")
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(real)
    return str(dest)


class TestEveryClassAnswersFromTheStagedTree:

    def test_the_check_passes_on_a_tree_that_carries_all_seven(self, mini):
        exit_code = tp.main([mini, "--check"])

        assert exit_code == 0

    def test_each_class_answers_from_the_half_it_declares(self, mini):
        measured = tp.measure(mini)

        assert {name: owner for name, (_path, owner) in measured.items()} == {
            row["name"]: row["owner"] for row in tp.CLASSES}

    def test_a_header_reads_the_search_path_not_its_realpath(self,
                                                             mini_symlinked):
        """The staged tree is what the sandbox mounts, so the question
        is which parameter reached the header - not where its bytes
        finally live once a symlink is followed."""
        row = next(one for one in tp.CLASSES if one["name"] == "gcc-headers")
        path = tp.resolve(mini_symlinked, row)

        assert path.startswith(mini_symlinked), \
            "the probe answered with the host copy the symlink points at"

    def test_a_pinned_closure_keeps_its_start_files_under_glibc(self,
                                                                tmp_path):
        """`UX-925`'s closure puts `crt1.o` in **glibc's** store path
        and `libgcc.a` in gcc's, so a `/usr/lib/*` glob alone writes a
        `-B` short of the tree - the silent case."""
        for path in ("nix/store/aaa-glibc-2.40/lib/crt1.o",
                     "nix/store/bbb-gcc-14.3.0/lib/gcc/x86_64/14/libgcc.a"):
            made = tmp_path / path
            made.parent.mkdir(parents=True)
            made.touch()

        found = tp.parameters(str(tmp_path))["prefixes"]

        assert found["crt1"] == f"{tmp_path}/nix/store/aaa-glibc-2.40/lib/"
        assert found["libgcc"] == (
            f"{tmp_path}/nix/store/bbb-gcc-14.3.0/lib/gcc/x86_64/14/")

    def test_a_relative_dest_reads_the_same_as_an_absolute_one(self, mini):
        """A relative `dest` makes relative `-B` flags, whose relative
        answers sit outside the absolute tree and read as the host's."""
        here = os.path.relpath(mini, os.getcwd())

        assert tp.measure(here) == tp.measure(mini)

    def test_the_three_prefixes_are_read_off_the_tree(self, mini):
        found = tp.parameters(mini)["prefixes"]

        assert sorted(found) == ["cc1", "crt1", "libgcc"]
        assert all(path is not None and path.startswith(mini)
                   for path in found.values())


class TestAParameterShortOfTheTreeReadsTheHost:
    """The mutation the row exists for. The driver sits outside the
    staged tree - the shim's own case, and `UX-925`'s, where the pin
    lives at its own `/nix/store/<hash>` - so a `-B` that does not
    reach is answered by this host's compiled-in prefix, silently."""

    @staticmethod
    def _short(mini, empty):
        """The shim's flags with the exec prefix pointed at a directory
        holding no `cc1`, rather than at the tree's own."""
        return [flag if "libexec" not in flag else f"-B{empty}{os.sep}"
                for flag in tp.flags_for(tp.parameters(mini))]

    def test_a_b_at_an_empty_directory_reads_the_hosts_cc1(self, mini, tmp_path):
        empty = tmp_path / "no-cc1-here"
        empty.mkdir()

        path, owner = tp.measure(mini, self._short(mini, empty),
                                 driver_root="/")["exec-prefix"]

        assert owner != tp.TOOLCHAIN, "the empty -B was answered from the tree"
        assert path is not None and not path.startswith(mini)
        assert "exec-prefix" not in tp.UNREADABLE_HERE, \
            "a class a parameter names is never excused for answering the host"

    def test_that_same_invocation_exits_zero_and_says_nothing(self, mini,
                                                              tmp_path):
        empty = tmp_path / "no-cc1-here"
        empty.mkdir()

        result = subprocess.run(["gcc", f"-B{empty}{os.sep}",
                                 "-print-prog-name=cc1"],
                                capture_output=True, text=True, timeout=60)

        assert result.returncode == 0 and result.stderr == "", \
            "gcc now reports an unusable -B, and this guard has less to prove"

    def test_the_check_reds_on_it_and_not_before(self, mini, tmp_path):
        empty = tmp_path / "no-cc1-here"
        empty.mkdir()
        whole = tp.flags_for(tp.parameters(mini))

        before = tp.divergences(mini, tp.measure(mini, whole, driver_root="/"))
        after = tp.divergences(mini, tp.measure(mini, self._short(mini, empty),
                                                driver_root="/"))

        assert "exec-prefix" not in [row[0] for row in before]
        assert "exec-prefix" in [row[0] for row in after]


class TestOnlyAClassNoParameterReachesIsExcused:
    """`mounted` - the host answering at a path the tree also carries -
    is the sandbox's own reading, not a broken parameter, but only for
    a class no flag names. `exec-prefix` under an empty `-B` lands in
    exactly the same state and is not excused."""

    def test_the_declared_class_warns_rather_than_reds(self, mini):
        outside = {"name": "cxx-headers", "owner": tp.SYSROOT,
                   "driver": "g++", "ask": ("header", "vector")}
        measured = dict(tp.measure(mini))
        measured["cxx-headers"] = ("/usr/include/c++/13/vector", tp.MOUNTED)

        assert tp.divergences(mini, measured) == []
        assert [name for name, _path
                in tp.unreadable_here(mini, measured)] == ["cxx-headers"]
        assert outside["name"] in tp.UNREADABLE_HERE

    def test_an_undeclared_class_in_the_same_state_reds(self, mini):
        measured = dict(tp.measure(mini))
        cc1 = tp.measure(mini)["exec-prefix"][0].replace(mini, "")
        measured["exec-prefix"] = (cc1, tp.MOUNTED)

        assert [row[0] for row in tp.divergences(mini, measured)] == \
            ["exec-prefix"]
        assert tp.unreadable_here(mini, measured) == []


class TestTheClassifierNormalizesFirst:
    """`-print-file-name=crt1.o` answers with `..` hops, so the raw
    string starts with the gcc libdir and reads as the toolchain's.
    The file is the target's."""

    def test_the_raw_answer_starts_inside_the_toolchains_own_directory(self,
                                                                       mini):
        """Asked with no parameters at all, which is how the driver
        answers before a shim gets near it."""
        raw = _ask_host("-print-file-name=crt1.o")

        assert ".." in raw
        assert tp.owner_of("/", raw) == tp.TOOLCHAIN

    def test_and_the_normalized_one_reads_the_target(self, mini):
        """Without the `-B` that names the multiarch directory, so the
        answer comes back with the hops rather than resolved by the
        flag - which is how a driver at its own prefix answers."""
        flags = [flag for flag in tp.flags_for(tp.parameters(mini))
                 if "x86_64" not in flag or "gcc" in flag]
        path, owner = tp.measure(mini, flags)["start-files"]

        assert ".." not in path
        assert owner == tp.SYSROOT


class TestTheShim:

    def test_it_is_shell_only(self, mini):
        text = tp.shim_text("/nix/store/h-gcc/bin/gcc", tp.parameters(mini))

        assert text.startswith("#!/bin/sh\n")
        for absent in ("dirname", "basename", "readlink", "$(", "`"):
            assert absent not in text, f"{absent} is not in the sandbox"

    def test_it_execs_rather_than_forks(self, mini):
        lines = [line for line in tp.shim_text("/x/gcc",
                                               tp.parameters(mini)).splitlines()
                 if line and not line.startswith("#")]

        assert len(lines) == 1 and lines[0].startswith("exec ")

    def test_it_hands_the_driver_every_parameter_and_the_argv(self, mini,
                                                              tmp_path):
        driver = tmp_path / "driver"
        driver.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
        driver.chmod(0o755)
        shim = tmp_path / "gcc"
        shim.write_text(tp.shim_text(str(driver), tp.parameters(mini)))
        shim.chmod(0o755)

        passed = subprocess.run([str(shim), "-c", "x.c"], capture_output=True,
                                text=True, timeout=60).stdout.splitlines()

        assert passed[-2:] == ["-c", "x.c"]
        assert passed[:-2] == tp.flags_for(tp.parameters(mini))

    def test_it_runs_where_the_stager_stages_no_coreutils(self, mini, tmp_path):
        """UX-918's trap, read off the stager's own axis arrays rather
        than a copy of them."""
        staged = _staged_names()
        assert "dirname" not in staged and "basename" not in staged, \
            "the stager now stages coreutils - this guard has nothing to prove"
        bin_dir = tmp_path / "staged-bin"
        bin_dir.mkdir()
        for name in sorted(staged):
            found = shutil.which(name)
            if found:
                (bin_dir / name).symlink_to(found)
        driver = tmp_path / "driver"
        driver.write_text('#!/bin/sh\nprintf OK\n')
        driver.chmod(0o755)
        shim = tmp_path / "gcc"
        shim.write_text(tp.shim_text(str(driver), tp.parameters(mini)))
        shim.chmod(0o755)

        result = subprocess.run([str(shim)], capture_output=True, text=True,
                                timeout=60, env={"PATH": str(bin_dir)})

        assert result.returncode == 0 and result.stdout == "OK", result.stderr


class TestAPrefixIsNeverWrittenAtNothing:

    def test_a_tree_with_no_cc1_refuses_to_write_a_shim(self, tmp_path,
                                                        capsys):
        exit_code = tp.main([str(tmp_path), "--shim", "gcc"])

        assert exit_code == 1
        assert "cc1" in capsys.readouterr().err

    def test_and_flags_for_leaves_a_missing_prefix_out(self, tmp_path):
        flags = tp.flags_for(tp.parameters(str(tmp_path)))

        assert flags == [f"--sysroot={tmp_path}"]


def _staged_names():
    """The basenames `stage_cpp_toolchain.sh` puts in the sandbox, read
    from both of its axis arrays."""
    text = STAGER.read_text()
    names = set()
    for array in ("RUNTIME_BINARIES", "TOOLCHAIN_BINARIES"):
        block = re.search(rf"^{array}=\((.*?)^\)", text, re.DOTALL | re.MULTILINE)
        assert block, f"stage_cpp_toolchain.sh no longer declares {array}=(...)"
        names |= {pathlib.PurePosixPath(word).name
                  for word in block.group(1).split() if word.startswith("/")}
    assert names, "no absolute paths read out of the stager's axis arrays"
    return names
