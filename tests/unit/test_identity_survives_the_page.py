"""UX-192: what the report prints has to survive being pasted back.

Round 19 closed the round-trip (`UX-178`) and the pip sentence
(`UX-181`) - and the same commit reopened both, one surface over. The
table elided identities longer than 43 characters, which is most real
forge urls, so the printed cell resolved as a *path* and answered
"rebuilds nothing here"; and `bga blast` built its keying sentence from
`resolved_as` (always `"url"`), so a pip resource claimed that any
commit rebuilt every element that installs it.

Both are the same failure: a surface describing a resource from
something other than the resource. The guards here paste and compare
rather than assert on a shape.
"""
import json
import os
import shutil
import types

import pytest

from bga import sources
from bga.blast import blast, format_blast_text
from bga.report.text import _format_resource_blast

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"

# 68 characters. Real: a GitLab subgroup path on a self-hosted forge is
# routinely this long, and the fixture UX-178 was accepted with (31
# chars) passed by staying under the elision threshold.
LONG_IDENTITY = "gitlab.example.com/some-org/platform/subgroup/monorepo-of-everything"


def _run(tmp_path, elements):
    run = tmp_path / "run"
    shutil.copytree(GOLDEN, run)
    os.remove(run / "expected_output.json")
    (run / "sources.json").write_text(json.dumps(sources.build_inventory(elements)))
    return run


def _table(inventory, downstream, kinds):
    rows = sources.resource_blast(inventory, downstream, kinds, {})
    result = types.SimpleNamespace(
        resource_blast={"rows": rows, "element_count": len(kinds)})
    return "\n".join(_format_resource_blast(result)), rows


def _git(identity):
    return {"kind": "git", "identity": identity, "declared": "https://" + identity,
            "keying": "ref", "staged_at": None}


class TestTheTableStaysPasteable:
    def _fixture(self, tmp_path):
        run = _run(tmp_path, {
            "base.bst": [_git(LONG_IDENTITY)],
            "lib.bst": [_git(LONG_IDENTITY)],
        })
        table, _rows = _table(
            json.loads((run / "sources.json").read_text()),
            {"base.bst": {"lib.bst"}, "lib.bst": set()},
            {"base.bst": "manual", "lib.bst": "manual"})
        return run, table

    def test_a_long_identity_is_printed_whole(self, tmp_path):
        _run_dir, table = self._fixture(tmp_path)
        assert LONG_IDENTITY in table, (
            "the identity is the join key - the next command a reader types "
            "is `bga blast <it>` - and it was elided to `...` + the tail")
        assert "..." not in table

    def test_the_printed_cell_round_trips(self, tmp_path):
        """The acceptance, by construction: read the identity back off
        the rendered page and hand it to the query."""
        run, table = self._fixture(tmp_path)
        printed = [line.strip() for line in table.splitlines()
                   if "monorepo-of-everything" in line]
        assert len(printed) == 1
        cell = printed[0]
        assert len(cell) > 43, f"the fixture is too short to test the bug: {cell}"

        answer = blast(run, cell, project_dir=str(tmp_path), measure=False)
        assert answer["resolved_as"] == "url", (
            f"the printed cell resolved as {answer['resolved_as']}")
        assert answer["direct_count"] == 2
        assert answer["kind"] == "git"

    def test_the_numbers_stay_in_their_columns(self, tmp_path):
        """The wrapped row keeps the alignment; `3/3unmeasured` (the
        blast and work columns colliding) was live beside the elision."""
        _run_dir, table = self._fixture(tmp_path)
        for line in table.splitlines():
            assert "unmeasured" not in line or line.count(" ") > 4


class TestTheSentenceComesFromTheSource:
    def _fixture(self, tmp_path, kind, identity, **extra):
        resource = {"kind": kind, "identity": identity, "declared": identity,
                    "keying": sources.keying_of(kind), "staged_at": None}
        resource.update(extra)
        return _run(tmp_path, {"lib.bst": [resource], "app.bst": [resource]})

    def test_a_pip_resource_is_not_described_as_a_repository(self, tmp_path):
        run = self._fixture(tmp_path, "pip", "requests @ pypi.org/simple")
        text = format_blast_text(
            blast(run, "requests @ pypi.org/simple", project_dir=str(tmp_path),
                  measure=False))
        assert "pinned version" in text
        assert "any commit" not in text, (
            "blast built the clause from `resolved_as`, so every ref-keyed "
            "resource got the git sentence")

    def test_a_tarball_gets_the_archive_sentence(self, tmp_path):
        run = self._fixture(tmp_path, "tar", "example.com/releases/foo-1.0.tar.xz")
        text = format_blast_text(
            blast(run, "example.com/releases/foo-1.0.tar.xz",
                  project_dir=str(tmp_path), measure=False))
        assert "archive" in text

    def test_a_git_resource_still_gets_the_commit_sentence(self, tmp_path):
        run = self._fixture(tmp_path, "git", "host/org/repo")
        text = format_blast_text(
            blast(run, "host/org/repo", project_dir=str(tmp_path), measure=False))
        assert "any commit" in text

    def test_an_ambiguous_kind_falls_back_rather_than_guessing(self, tmp_path):
        """Two kinds answering one spelling: the keying-only wording is
        right, and picking one of them at random is not."""
        run = _run(tmp_path, {
            "lib.bst": [{"kind": "local", "identity": "files/shared",
                         "declared": "files/shared", "keying": "content",
                         "staged_at": None}],
            "app.bst": [{"kind": "patch", "identity": "files/shared",
                         "declared": "files/shared", "keying": "content",
                         "staged_at": None}],
        })
        answer = blast(run, "files/shared/x.c", project_dir=str(tmp_path),
                       measure=False)
        assert answer["kind"] is None
        assert "keys on content" in format_blast_text(answer)


class TestBlastGroupsTheWayTheTableGroups:
    def test_two_kinds_sharing_a_spelling_do_not_merge(self, tmp_path):
        """The table groups by `(kind, identity)`; blast grouped by
        identity alone, so the two surfaces reported different counts
        for the same run."""
        local = {"kind": "local", "identity": "files/shared",
                 "declared": "files/shared", "keying": "content", "staged_at": None}
        patch = dict(local, kind="patch")
        run = _run(tmp_path, {
            "base.bst": [local], "lib.bst": [local],
            "app.bst": [patch], "extra.bst": [patch],
        })
        inventory = json.loads((run / "sources.json").read_text())
        _table_text, rows = _table(
            inventory, {uid: set() for uid in inventory["elements"]},
            {uid: "manual" for uid in inventory["elements"]})

        assert sorted(row["kind"] for row in rows) == ["local", "patch"]
        assert [row["direct_count"] for row in rows] == [2, 2]

        answer = blast(run, "files/shared", project_dir=str(tmp_path), measure=False)
        assert answer["direct_count"] == 2, (
            "blast merged both kinds into one answer the table never showed")


class TestAJunctionedPathIsReachableFromTheFilesystem:
    def test_the_namespaced_identity_answers_to_the_path_a_developer_types(
            self, tmp_path):
        """UX-182 namespaced content identities by junction
        (`sub.bst:files/libfoo`), which is right for the table and
        unreachable from the only spelling a developer has: the path."""
        run = _run(tmp_path, {
            "sub.bst:libfoo.bst": [{
                "kind": "local", "identity": "sub.bst:files/libfoo",
                "declared": "files/libfoo", "keying": "content",
                "staged_at": None}],
        })
        by_path = blast(run, "files/libfoo/src/main.c", project_dir=str(tmp_path),
                        measure=False)
        assert by_path["direct_elements"] == ["sub.bst:libfoo.bst"]

        exact = blast(run, "sub.bst:files/libfoo", project_dir=str(tmp_path),
                      measure=False)
        assert exact["direct_elements"] == ["sub.bst:libfoo.bst"], (
            "the printed, namespaced form must still resolve exactly")


class TestTheRemainingUrlSeams:
    @pytest.mark.parametrize("url,expected", [
        # A colon in the *path*: forges permit it, and the scp rewrite
        # used to turn it into a second identity for one repository.
        ("https://host/a:b/c", "host/a:b/c"),
        ("https://host:8443/org/repo", "host:8443/org/repo"),
        # scp-style, which is what the rewrite is actually for.
        ("git@host:org/repo.git", "host/org/repo"),
    ])
    def test_a_colon_below_the_host_is_left_alone(self, url, expected):
        assert sources.normalize_url(url) == expected

    def test_git_plus_http_folds_with_http(self):
        """`git+https` was known and `git+http` was not, so the same
        repository over plain http had two identities."""
        assert (sources.normalize_url("git+http://host/org/repo.git")
                == sources.normalize_url("http://host/org/repo"))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
