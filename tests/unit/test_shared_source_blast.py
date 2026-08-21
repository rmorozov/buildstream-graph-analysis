"""UX-171: the blast question a monorepo actually asks.

Every blast question the tool could answer started at an element -
"change `core.bst` and 84 things rebuild". A monorepo raises the
question one level down: *this repo was touched, how many recipes
rebuild, and what does that cost?*

The mechanism these tests pin: a `git` source keys on its **ref**, so
`directory:` changes where a checkout is staged and not what it is
keyed on - twenty elements sourcing one url all rebuild on any commit
to that repository. A `local` source keys on **content**, so only the
elements whose files changed rebuild. The same monorepo consumed two
ways differs by an order of magnitude, and the `.bst` files say which
way it is consumed.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from bga import sources
from tools.bst_extract_run import build_source_inventory


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO_ROOT, "tests", "fixtures", "golden", "mixed_task_kinds")


def _project(tmp_path, elements):
    """A project directory of `.bst` files and nothing else."""
    project = tmp_path / "proj"
    (project / "elements").mkdir(parents=True)
    (project / "project.conf").write_text(
        "name: blast\nmin-version: 2.0\nelement-path: elements\n")
    for name, body in elements.items():
        (project / "elements" / name).write_text(body)
    return str(project)


def _git_element(url, directory, depends=()):
    lines = ["kind: manual", "sources:", "- kind: git",
             f"  url: {url}", f"  directory: {directory}", "  ref: 0" * 0]
    lines = [line for line in lines if line]
    if depends:
        lines.append("depends:")
        lines.extend(f"- filename: {d}\n  type: build" for d in depends)
    return "\n".join(lines) + "\n"


def _local_element(path, depends=()):
    lines = ["kind: manual", "sources:", "- kind: local", f"  path: {path}"]
    if depends:
        lines.append("depends:")
        lines.extend(f"- filename: {d}\n  type: build" for d in depends)
    return "\n".join(lines) + "\n"


class TestOneRepositoryConsumedTwoWays:
    """The acceptance's own comparison, on the same graph shape."""

    MONO = "https://gitlab.example.com/org/monorepo.git"

    def _graph(self):
        """Six libs off a core, an app on all six - `examples/06`'s shape."""
        libs = [f"lib-{c}.bst" for c in "abcdef"]
        downstream = {uid: {"app.bst"} for uid in libs}
        downstream["core.bst"] = set(libs) | {"app.bst"}
        downstream["app.bst"] = set()
        kinds = {uid: "cmake" for uid in libs}
        kinds["core.bst"] = "manual"
        kinds["app.bst"] = "cmake"
        return libs, downstream, kinds

    def test_a_shared_git_url_blasts_every_consumer(self, tmp_path):
        libs, downstream, kinds = self._graph()
        elements = {uid: _git_element(self.MONO, f"src/{uid[:-4]}", ["core.bst"])
                    for uid in libs}
        elements["core.bst"] = _local_element("files/core")
        elements["app.bst"] = _local_element("files/app", libs)
        project = _project(tmp_path, elements)

        inventory = build_source_inventory(project, sorted(elements))
        rows = sources.resource_blast(inventory, downstream, kinds,
                                      {uid: 100.0 for uid in kinds})
        assert len(rows) == 1, rows
        row = rows[0]
        assert row["identity"] == "gitlab.example.com/org/monorepo"
        assert row["direct_count"] == 6
        # The six, plus the app they all feed. `core.bst` is upstream of
        # them, so it is not in the blast - a commit to the monorepo does
        # not rebuild what the monorepo consumes.
        assert row["blast_count"] == 7
        assert row["by_element_kind"] == {"cmake": 7}
        assert row["measured_seconds"] == pytest.approx(700.0)
        assert "keys on ref" in sources.keying_clause(row)
        # Six different staging directories, one identity - which is the
        # whole trap.
        assert len(row["staged_at"]) == 6

    def test_the_same_repo_as_local_paths_blasts_per_directory(self, tmp_path):
        libs, downstream, kinds = self._graph()
        elements = {uid: _local_element(f"files/src/{uid[:-4]}", ["core.bst"])
                    for uid in libs}
        elements["core.bst"] = _local_element("files/core")
        elements["app.bst"] = _local_element("files/app", libs)
        project = _project(tmp_path, elements)

        inventory = build_source_inventory(project, sorted(elements))
        rows = sources.resource_blast(inventory, downstream, kinds, {})
        # Every path is its own resource, sourced by exactly one element,
        # so nothing is shared and there is no row at all.
        assert rows == []
        # The inventory still knows what each element sources.
        assert inventory["elements"]["lib-a.bst"][0]["keying"] == "content"
        assert inventory["elements"]["lib-a.bst"][0]["identity"] == "files/src/lib-a"

    def test_the_headline_fires_only_when_one_repo_dominates(self, tmp_path):
        libs, downstream, kinds = self._graph()
        elements = {uid: _git_element(self.MONO, f"src/{uid[:-4]}", ["core.bst"])
                    for uid in libs}
        elements["core.bst"] = _local_element("files/core")
        elements["app.bst"] = _local_element("files/app", libs)
        project = _project(tmp_path, elements)
        inventory = build_source_inventory(project, sorted(elements))
        rows = sources.resource_blast(inventory, downstream, kinds,
                                      {uid: 3600.0 for uid in kinds})

        # 7 of 8 elements is most of the graph.
        headline = sources.monorepo_headline(rows, element_count=8)
        assert headline is not None
        assert "monorepo" in headline and "7 of 8" in headline
        assert "7.0h" in headline, headline
        # A 22s build must not be headlined as "0.0h" (found live on
        # the real `examples/01` capture this was verified against).
        assert sources.format_work(22.544) == "23s"
        # The same rows against a graph they are a small corner of.
        assert sources.monorepo_headline(rows, element_count=400) is None

    def test_a_content_keyed_resource_never_raises_the_headline(self, tmp_path):
        """Shared *and* content-keyed is not the monorepo problem.

        Six elements staging one directory rebuild together because
        their files changed - which is what a cache key is for.
        """
        libs, downstream, kinds = self._graph()
        elements = {uid: _local_element("files/shared", ["core.bst"]) for uid in libs}
        elements["core.bst"] = _local_element("files/core")
        elements["app.bst"] = _local_element("files/app", libs)
        project = _project(tmp_path, elements)
        inventory = build_source_inventory(project, sorted(elements))
        rows = sources.resource_blast(inventory, downstream, kinds, {})
        assert len(rows) == 1 and rows[0]["keying"] == "content"
        assert sources.monorepo_headline(rows, element_count=8) is None


class TestTheInventoryNamesWhatItCannotRead:
    def test_an_unfetched_junction_is_counted_not_guessed(self, tmp_path):
        """A junction that is not on disk cannot be read, and says so.

        UX-160's lesson: a reader that silently drops what it cannot
        parse reports zero and looks like an answer. UX-182 walks into
        junctions that *are* checked out; this is the other half.
        """
        project = _project(tmp_path, {"local.bst": _local_element("files/x")})
        inventory = build_source_inventory(
            project, ["local.bst", "sub.bst:remote.bst"])
        assert "local.bst" in inventory["elements"]
        assert "sub.bst:remote.bst" not in inventory["elements"]
        assert "not checked out here" in \
            " ".join(inventory["unreadable"]["sub.bst:remote.bst"])

    def test_an_unreadable_stanza_is_named(self, tmp_path):
        project = _project(tmp_path, {
            "odd.bst": "kind: manual\nsources:\n- kind: mystery\n  spelling: wrong\n",
        })
        inventory = build_source_inventory(project, ["odd.bst"])
        assert inventory["elements"] == {}
        assert "mystery" in " ".join(inventory["unreadable"]["odd.bst"])

    def test_an_element_with_no_sources_is_neither(self, tmp_path):
        project = _project(tmp_path, {"stack.bst": "kind: stack\n"})
        inventory = build_source_inventory(project, ["stack.bst"])
        assert inventory["elements"] == {} and inventory["unreadable"] == {}


class TestUrlIdentity:
    @pytest.mark.parametrize("url", [
        "https://gitlab.example.com/org/monorepo.git",
        "https://gitlab.example.com/org/monorepo",
        "git@gitlab.example.com:org/monorepo.git",
        "ssh://git@gitlab.example.com/org/monorepo.git",
        "https://gitlab.example.com/org/monorepo/",
    ])
    def test_one_repository_has_one_identity(self, url):
        """Two spellings reported separately would halve the blast."""
        assert sources.normalize_url(url) == "gitlab.example.com/org/monorepo"

    def test_a_port_is_not_a_path(self):
        assert sources.normalize_url("ssh://git@host:2222/org/repo.git") == \
            "host:2222/org/repo"

    def test_different_repositories_stay_different(self):
        assert sources.normalize_url("https://host/org/one") != \
            sources.normalize_url("https://host/org/two")


class TestItReachesTheReport:
    """The section, end to end, through `bga analyze`."""

    def _run_dir(self, tmp_path, inventory=None, name="run"):
        run = tmp_path / name
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        if inventory is not None:
            (run / "sources.json").write_text(json.dumps(inventory, indent=2))
        return run

    def _analyze(self, run, extra=()):
        return subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", str(run), *extra],
            capture_output=True, text=True, cwd=REPO_ROOT, check=True,
        ).stdout

    def test_a_run_with_a_shared_resource_prints_the_table(self, tmp_path):
        shared = {"kind": "git", "identity": "host/org/mono", "declared":
                  "https://host/org/mono.git", "keying": "ref", "staged_at": "src/lib"}
        inventory = sources.build_inventory({
            "lib.bst": [dict(shared, staged_at="src/lib")],
            "extra.bst": [dict(shared, staged_at="src/extra")],
        })
        text = self._analyze(self._run_dir(tmp_path, inventory))
        assert "Shared Sources" in text
        assert "host/org/mono" in text
        assert "keys on ref" in text
        assert "not wall clock" in text

    def test_the_json_carries_the_same_rows(self, tmp_path):
        shared = {"kind": "git", "identity": "host/org/mono", "declared":
                  "https://host/org/mono.git", "keying": "ref", "staged_at": None}
        inventory = sources.build_inventory({
            "lib.bst": [shared], "extra.bst": [shared],
        })
        payload = json.loads(self._analyze(self._run_dir(tmp_path, inventory),
                                           ["--format", "json"]))
        rows = payload["resource_blast"]["rows"]
        assert [row["identity"] for row in rows] == ["host/org/mono"]
        assert rows[0]["direct_elements"] == ["extra.bst", "lib.bst"]

    def test_a_run_without_an_inventory_says_nothing(self, tmp_path):
        """Every capture taken before UX-171 is one of these."""
        run = self._run_dir(tmp_path)
        text = self._analyze(run)
        assert "Shared Sources" not in text
        payload = json.loads(self._analyze(run, ["--format", "json"]))
        assert "resource_blast" not in payload

    def test_a_run_whose_project_shares_nothing_says_nothing(self, tmp_path):
        inventory = sources.build_inventory({
            "lib.bst": [{"kind": "local", "identity": "files/lib",
                         "declared": "files/lib", "keying": "content",
                         "staged_at": None}],
        })
        text = self._analyze(self._run_dir(tmp_path, inventory))
        assert "Shared Sources" not in text


class TestTheRenderersAgree:
    def _result(self, rows, headline=None):
        class _Result:
            pass
        result = _Result()
        result.resource_blast = {
            'rows': rows, 'element_count': 10, 'headline': headline,
            'unreadable': {},
        }
        return result

    def test_an_unmeasured_row_says_so_rather_than_zero(self):
        from bga.report.text import _format_resource_blast
        rows = [{
            "kind": "git", "identity": "host/repo", "keying": "ref",
            "direct_elements": ["a.bst", "b.bst"], "direct_count": 2,
            "blast_elements": ["a.bst", "b.bst"], "blast_count": 2,
            "by_element_kind": {"manual": 2}, "measured_seconds": None,
            "measured_elements": 0, "staged_at": [],
        }]
        text = "\n".join(_format_resource_blast(self._result(rows)))
        assert "unmeasured" in text
        assert " 0s" not in text


BST_AVAILABLE = shutil.which("bst") is not None
FIXTURE_PROJECT = os.path.join(REPO_ROOT, "tests", "fixtures", "bst_show_project")


@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH")
def test_a_real_extraction_writes_the_inventory(tmp_path):
    """The producer wiring, on a real `bst` extraction.

    Everything else here builds the inventory directly and hands it to
    the report. That would keep passing with `extract_run` never
    writing `sources.json` at all - which is exactly the shape UX-176
    complains about, and it was found by mutating this file's own
    producer and watching nothing go red.
    """
    from tests.unit._bst_env import isolated_bst_env
    from tools.bst_extract_run import extract_run

    log = tmp_path / "build.log"
    proc = subprocess.run(
        ["bst", "-C", FIXTURE_PROJECT, "--no-colors", "build", "app.bst"],
        capture_output=True, text=True, env=isolated_bst_env(tmp_path),
    )
    log.write_text(proc.stdout + proc.stderr)

    out = tmp_path / "run"
    extract_run(FIXTURE_PROJECT, str(log), str(out), log_format="auto")

    inventory = json.loads((out / "sources.json").read_text())
    assert inventory["schema"] == sources.SCHEMA
    assert inventory["elements"]["base.bst"] == [{
        "kind": "local", "identity": "files/base", "declared": "files/base",
        "keying": "content", "staged_at": None,
    }]
    # UX-182 changed this deliberately. The junctioned element's sources
    # used to be reported `unreadable`, which was honest but useless on
    # exactly the projects the monorepo question comes from - they keep
    # most elements behind junctions. The junction is sourced locally
    # here, so the subproject is on disk and gets read; its
    # content-keyed path is namespaced to the junction, because
    # `files/libfoo` means a different directory in each project.
    assert inventory["elements"]["subproj-junction.bst:libfoo.bst"] == [{
        "kind": "local", "identity": "subproj-junction.bst:files/libfoo",
        "declared": "files/libfoo", "keying": "content", "staged_at": None,
    }]
    assert inventory["unreadable"] == {}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))