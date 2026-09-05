"""UX-410: a `--project` that is not a project built one anyway.

Found by the round-64 walker's own mistyped relative path. With the
working directory already inside example 06:

```text
bga snapshot --project examples/06-macro-micro-optimization -- bst build all.bst
```

`examples/06-.../examples/06-...` does not exist - and path resolution
made one anyway. `snapshot` created `.bga` under the phantom directory,
ran `bst` with it as the working directory, and **bst walked up to the
real `project.conf` and built the parent project**. Green snapshot,
store in a directory the user never meant, measuring a build of a
project the flag never named.

`bga doctor` has checked for `project.conf` since `UX-125`. The command
that *writes a store* did not - the same fact, known by one command and
not by the one that acts on it.

Refused before anything is written, which is `UX-324`'s rule and
`UX-324`'s place in `main`: the snapshot directory, the sticky config
and the store's `.gitignore` are all created on the way past there. The
directory-listing clause below is that item's own acceptance shape.
"""
import io
import os
import pathlib
import sys
from contextlib import redirect_stderr

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import bga_snapshot


def _listing(root: pathlib.Path):
    """Every path under `root`, so "wrote nothing" is checkable."""
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


class TestTheRefusal:
    def test_a_directory_with_no_project_conf_is_refused(self, tmp_path):
        (tmp_path / "notaproject").mkdir()
        said = bga_snapshot.why_the_project_is_not_one(
            str(tmp_path / "notaproject"))
        assert said, (
            "a directory with no project.conf was accepted, and bst walked "
            "up and built the enclosing project instead")
        assert "project.conf" in said, (
            "the refusal names what it looked for; a reader who is told "
            "'not a project' and not what a project *is* cannot act on it")

    def test_a_path_that_does_not_exist_says_so(self, tmp_path):
        """Two mistakes, told apart.

        The walker hit the second one, and "it has no project.conf"
        would have sent them looking for a file in a directory that is
        not there.
        """
        said = bga_snapshot.why_the_project_is_not_one(
            str(tmp_path / "nowhere"))
        assert said and "does not exist" in said, said

    def test_the_refusal_names_the_project_bst_would_have_built(self, tmp_path):
        """The whole point: the enclosing project is the silent answer."""
        (tmp_path / "project.conf").write_text("name: real\n")
        (tmp_path / "inner").mkdir()
        said = bga_snapshot.why_the_project_is_not_one(str(tmp_path / "inner"))
        # `f"nearest project above it is {tmp_path}"`, not `tmp_path in
        # said`: the refused path is *inside* `tmp_path`, so the bare
        # substring is already in the first line and the clause passed
        # with the whole enclosing-project sentence deleted. Found by
        # the mutation that deleted it.
        assert said and f"nearest project above it is {tmp_path}" in said, (
            f"the refusal must name the project bst would have walked up "
            f"to and built; it said: {said}")

    def test_a_real_project_is_not_refused(self, tmp_path):
        (tmp_path / "project.conf").write_text("name: real\n")
        assert bga_snapshot.why_the_project_is_not_one(str(tmp_path)) is None


class TestNothingIsWritten:
    """`UX-324`'s clause, applied to the flag."""

    def test_the_refusal_leaves_the_directory_byte_for_byte(self, tmp_path,
                                                            monkeypatch):
        target = tmp_path / "notaproject"
        target.mkdir()
        before = _listing(tmp_path)

        monkeypatch.chdir(tmp_path)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = bga_snapshot.main(
                ["--project", str(target), "--", "bst", "build", "all.bst"])

        assert code == 2, (
            f"a refusal exits 2 like every other one in this command; "
            f"got {code}")
        assert "Nothing was captured and nothing was written" in stderr.getvalue()
        assert _listing(tmp_path) == before, (
            "the refusal path created something. `UX-324` found a snapshot "
            "directory with build.log and an empty plane2.log left behind by "
            "a capture that could not start; this is the same clause one "
            "flag over")
        assert not os.path.exists(target / ".bga"), (
            "the store was created under a directory that is not a project")

    def test_an_omitted_flag_still_resolves_the_enclosing_project(self,
                                                                  tmp_path,
                                                                  monkeypatch):
        """Resolving upward from a subdirectory is the documented way in.

        The check runs on the resolved root too, and cannot fail there:
        `run_store.project_root` finds a root *by* looking for exactly
        this file. This clause holds that equivalence - if the resolver
        ever starts returning something else, the documented invocation
        would begin refusing itself.
        """
        (tmp_path / "project.conf").write_text("name: real\n")
        inner = tmp_path / "inner"
        inner.mkdir()
        monkeypatch.chdir(inner)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = bga_snapshot.main(["--list"])
        assert code == 0, stderr.getvalue()
        assert "not a BuildStream project" not in stderr.getvalue(), (
            "resolving upward from a subdirectory is the documented way to "
            "run this, and it must not trip the flag's check")
