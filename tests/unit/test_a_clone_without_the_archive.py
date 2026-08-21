"""UX-189: a clone should not ship the capture archive.

Field feedback: *"it's not very comfortable to clone our repo and get
binary data from captures — maybe we need to fix doc to clone only main
branch."*

Measured against the real remote, round 20: eight `captures/*` branches,
and the default clone takes all of them.

    $ git clone https://github.com/rmorozov/buildstream-graph-analysis
    $ du -sh .git                     ->  50M     15 remote refs, 8 captures/*
    $ git clone --single-branch ...
    $ du -sh .git                     ->  5.3M     2 remote refs, 0 captures/*

The branches are load-bearing, so the fix is at the clone rather than at
the archive - and the check that this is *safe* is that `bga baseline`
still works from the narrowed clone. It does: it discovers with
`git ls-remote` and reads through `FETCH_HEAD`, neither of which cares
what the clone's refspec is. Run against the real remote from a
`--single-branch` clone it fetched both captures of the named shape and
then refused on a content ground (`trace_spine differs`), which is the
answer that clone shape has nothing to do with.

One thing did break, and it is why item 3 exists: in a `--single-branch`
clone `refs/remotes/origin/captures/*` is never created, so the
capture-workflow doc's own

    git show origin/captures/fdsdk-latest:capture.tar.gz

failed with `fatal: invalid object name` (exit 128). Documenting the
narrow clone without fixing that line would have broken the workflow the
narrow clone points people at.

The guards below run against a local bare repository shaped like the
remote, so they need no network and assert git's real behaviour rather
than a description of it.
"""
import random
import re
import subprocess

import pytest

DOCS_WITH_THE_CLONE = ("README.md", "docs/guides/real-project.md")
CAPTURE_BRANCHES = ("captures/fdsdk-latest",
                    "captures/fdsdk/953683fb-incremental-b4j4-32223468993")


def _git(*args, cwd=None):
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                            text=True)
    assert result.returncode == 0, f"git {' '.join(args)}: {result.stderr}"
    return result.stdout


def _clone(remote, target, *flags):
    """Clone with the real transfer path.

    `--no-local`, always: a `git clone` of a path on the same filesystem
    hardlinks the entire object store and ignores `--single-branch` for
    the purpose of what lands on disk. The first draft of the size guard
    below measured that artefact and reported 828919 B against
    829110 B - two numbers that had nothing to do with the flag under
    test. Over http, which is how a user clones this, the narrow clone
    negotiates for main's objects alone.
    """
    _git("clone", "-q", "--no-local", *flags, str(remote), str(target))


@pytest.fixture(scope="module")
def remote(tmp_path_factory):
    """A bare repository with a `main` and two `captures/*` branches.

    The capture branches carry a payload, so "did the clone take them"
    is answerable by size as well as by ref.
    """
    work = tmp_path_factory.mktemp("work")
    _git("init", "-q", "-b", "main", str(work))
    _git("config", "user.email", "t@example.com", cwd=work)
    _git("config", "user.name", "t", cwd=work)
    (work / "README.md").write_text("the tool\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-qm", "main", cwd=work)

    for index, branch in enumerate(CAPTURE_BRANCHES):
        _git("checkout", "-q", "--orphan", f"c{index}", cwd=work)
        _git("rm", "-rq", "--cached", ".", cwd=work)
        (work / "README.md").unlink(missing_ok=True)
        # Incompressible, so the branch costs real bytes the way a
        # `capture.tar.gz` does. Seeded rather than `urandom` so a
        # failure reproduces; the first draft used an arithmetic
        # sequence, which zlib flattened to nothing and left the
        # size guard below asserting 35 KiB against 35 KiB.
        (work / "capture.tar.gz").write_bytes(
            random.Random(index).randbytes(400_000))
        (work / "capture-outcome.txt").write_text("traced_build_exit=0\n")
        _git("add", "-A", cwd=work)
        _git("commit", "-qm", f"capture {index}", cwd=work)
        _git("branch", "-M", branch, cwd=work)

    _git("checkout", "-q", "main", cwd=work)
    bare = tmp_path_factory.mktemp("bare") / "remote.git"
    _git("clone", "-q", "--bare", str(work), str(bare))
    return bare


def _documented_clone_flags():
    """The flags the docs actually tell a user to pass.

    Read out of the docs rather than hardcoded, so the guard cannot pass
    against a clone command the docs no longer contain.
    """
    flags = set()
    for doc in DOCS_WITH_THE_CLONE:
        for line in open(doc, encoding="utf-8"):
            if "git clone" in line and "buildstream-graph-analysis" in line:
                flags |= {word for word in line.split() if word.startswith("--")}
    assert flags, f"no `git clone` of this repository in {DOCS_WITH_THE_CLONE}"
    return sorted(flags)


class TestTheDocumentedClone:
    def test_it_fetches_no_capture_refs(self, remote, tmp_path):
        """The acceptance test, run against git rather than described."""
        target = tmp_path / "narrow"
        _clone(remote, target, *_documented_clone_flags())

        refs = _git("branch", "-r", cwd=target).split()
        assert not [ref for ref in refs if "captures/" in ref], (
            f"the documented clone fetched capture refs: {refs}")

    def test_the_default_clone_does_fetch_them(self, remote, tmp_path):
        """The other half of the claim: without the flag they arrive.

        Without this, the guard above would pass just as well against a
        remote that has no capture branches at all - which is to say it
        would be asserting nothing.
        """
        target = tmp_path / "wide"
        _clone(remote, target)

        refs = _git("branch", "-r", cwd=target).split()
        assert len([ref for ref in refs if "captures/" in ref]) == \
            len(CAPTURE_BRANCHES), refs

    def test_it_is_smaller(self, remote, tmp_path):
        def size(path):
            return sum(item.stat().st_size
                       for item in (path / ".git").rglob("*") if item.is_file())

        _clone(remote, tmp_path / "narrow", *_documented_clone_flags())
        _clone(remote, tmp_path / "wide")
        narrow, wide = size(tmp_path / "narrow"), size(tmp_path / "wide")
        assert narrow * 2 < wide, (
            f"narrow clone {narrow} B is not meaningfully smaller than "
            f"{wide} B - the fixture's capture branches must carry payload "
            f"for this to mean anything")


class TestFetchingOnDemandStillWorks:
    """The narrow clone must not cost a user the archive, only the
    up-front download of it."""

    def test_the_documented_refspec_brings_a_capture_back(self, remote, tmp_path):
        target = tmp_path / "narrow"
        _clone(remote, target, *_documented_clone_flags())

        ref = CAPTURE_BRANCHES[0]
        _git("fetch", "-q", "origin", f"{ref}:{ref}", cwd=target)
        assert "traced_build_exit=0" in _git(
            "show", f"{ref}:capture-outcome.txt", cwd=target)

    def test_fetch_head_works_too(self, remote, tmp_path):
        """The form `bga baseline` uses, and the one the workflow doc's
        untar and `checkout -- run` lines now use."""
        target = tmp_path / "narrow"
        _clone(remote, target, *_documented_clone_flags())

        _git("fetch", "-q", "origin", CAPTURE_BRANCHES[0], cwd=target)
        assert "traced_build_exit=0" in _git(
            "show", "FETCH_HEAD:capture-outcome.txt", cwd=target)

    def test_the_remote_tracking_form_does_not(self, remote, tmp_path):
        """The measured breakage, pinned so the docs cannot drift back.

        `git show origin/captures/...` is what the workflow doc said
        before `UX-189`; under the clone `UX-189` documents it is
        `fatal: invalid object name`.
        """
        target = tmp_path / "narrow"
        _clone(remote, target, *_documented_clone_flags())
        _git("fetch", "-q", "origin", CAPTURE_BRANCHES[0], cwd=target)

        result = subprocess.run(
            ["git", "show", f"origin/{CAPTURE_BRANCHES[0]}:capture-outcome.txt"],
            cwd=target, capture_output=True, text=True)
        assert result.returncode != 0
        assert "invalid object name" in result.stderr


class TestTheDocsSayIt:
    def test_both_front_doors_document_the_narrow_clone(self):
        for doc in DOCS_WITH_THE_CLONE:
            text = open(doc, encoding="utf-8").read()
            assert re.search(r"git clone --single-branch\s+http", text), (
                f"{doc} does not document the clone")

    def test_they_say_why(self):
        """A flag with no reason gets dropped by the next person to edit
        the line."""
        for doc in DOCS_WITH_THE_CLONE:
            text = open(doc, encoding="utf-8").read()
            assert "captures/" in text, f"{doc} does not say what it skips"

    def test_no_doc_tells_a_user_to_read_a_remote_tracking_capture_ref(self):
        """`git show origin/captures/...` cannot work under the clone
        these docs now recommend."""
        import pathlib

        offenders = []
        for path in pathlib.Path(".").rglob("*.md"):
            if "backlog/scenarios" in str(path) or "audits/" in str(path):
                continue   # task files and audit rounds quote the defect
            fenced = False
            for number, line in enumerate(
                    open(path, encoding="utf-8").read().splitlines(), 1):
                if line.lstrip().startswith("```"):
                    fenced = not fenced
                    continue
                # Only commands a user would run. Prose *about* the
                # broken form is the point of the fix, not a violation
                # of it - the first draft of this guard flagged its own
                # explanation.
                if fenced and re.search(
                        r"git (show|checkout|archive)\b.*origin/captures/", line):
                    offenders.append(f"{path}:{number}: {line.strip()}")
        assert not offenders, "\n".join(offenders)

    def test_the_workflow_doc_documents_fetching_on_demand(self):
        text = open("docs/design/capture-workflow.md", encoding="utf-8").read()
        assert "git fetch origin captures/fdsdk-latest:captures/fdsdk-latest" \
            in text


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
