"""UX-833: a custom source plugin, declared onto a kind bga already keys.

`bga/blast.py` names a source kind by heuristic over the kinds
BuildStream ships - a project sourcing through a Gerrit plugin or an
internal mirror matches nothing. `bga-source-kinds` (beside
`bga-foundation`) maps the custom kind onto a known one, whose keying
it then inherits; a kind still unmapped is named in
`resource_blast.unmapped_source_kinds`, never silently folded into an
unestimated blast.
"""
import json
import os
import pathlib
import shutil
import subprocess

import pytest

from bga import sources
from tools.bst_extract_run import _read_bga_source_kind_map, build_source_inventory

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _project(tmp_path, elements, declaration=None):
    """A project directory of `.bst` files, optionally declaring
    `bga-source-kinds`."""
    project = tmp_path / "proj"
    (project / "elements").mkdir(parents=True)
    variables = f"variables:\n  bga-source-kinds: {declaration}\n" if declaration else ""
    (project / "project.conf").write_text(
        f"name: p\nmin-version: 2.0\nelement-path: elements\n{variables}")
    for name, body in elements.items():
        (project / "elements" / name).write_text(body)
    return project


def _source_element(kind, url, directory):
    return (f"kind: manual\nsources:\n- kind: {kind}\n"
            f"  url: {url}\n  directory: {directory}\n")


class TestAMappedKindKeysLikeTheKindItInherits:
    URL = "https://example.com/org/repo.git"

    def _rows(self, tmp_path, name, kind, kind_map=None):
        elements = {"a.bst": _source_element(kind, self.URL, "src/a"),
                    "b.bst": _source_element(kind, self.URL, "src/b")}
        project = _project(tmp_path / name, elements)
        inventory = build_source_inventory(project, sorted(elements), kind_map)
        downstream = {"a.bst": set(), "b.bst": set()}
        kinds = {"a.bst": "manual", "b.bst": "manual"}
        durations = {"a.bst": 100, "b.bst": 200}
        return sources.resource_blast(inventory, downstream, kinds, durations)

    def test_a_mapped_gerrit_element_blasts_like_git(self, tmp_path):
        mapped = self._rows(tmp_path, "mapped", "gerrit", {"gerrit": "git"})
        plain = self._rows(tmp_path, "plain", "git")
        assert len(mapped) == len(plain) == 1
        mapped_row, plain_row = mapped[0], plain[0]
        assert mapped_row["kind"] == "gerrit"
        assert plain_row["kind"] == "git"
        for key in mapped_row:
            if key == "kind":
                continue
            assert mapped_row[key] == plain_row[key], key

    def test_unmapped_gerrit_is_named_not_folded_silently(self, tmp_path):
        rows = self._rows(tmp_path, "unmapped", "gerrit")
        assert rows and rows[0]["keying"] == "unknown"

    def test_the_coverage_block_names_the_unmapped_kind(self, tmp_path):
        elements = {"a.bst": _source_element("gerrit", self.URL, "src/a")}
        project = _project(tmp_path, elements)
        inventory = build_source_inventory(project, sorted(elements))
        assert sources.unmapped_kinds(inventory) == ["gerrit"]

    def test_a_mapped_kind_never_appears_unmapped(self, tmp_path):
        elements = {"a.bst": _source_element("gerrit", self.URL, "src/a")}
        project = _project(tmp_path, elements)
        inventory = build_source_inventory(
            project, sorted(elements), {"gerrit": "git"})
        assert sources.unmapped_kinds(inventory) == []
        assert inventory["source_kind_map"] == {"gerrit": "git"}


class TestNoDeclarationIsTodaysBehaviour:
    def test_the_map_is_empty_and_nothing_is_unmapped(self, tmp_path):
        elements = {"a.bst": _source_element("git",
                                             "https://example.com/o/r.git", "src")}
        project = _project(tmp_path, elements)
        inventory = build_source_inventory(project, sorted(elements))
        assert inventory["source_kind_map"] == {}
        assert sources.unmapped_kinds(inventory) == []

    def test_a_missing_project_conf_reads_as_no_declaration(self, tmp_path):
        assert _read_bga_source_kind_map(str(tmp_path)) is None


class TestExtractionRejectsAMalformedDeclaration:
    def _project_conf(self, tmp_path, declaration):
        (tmp_path / "elements").mkdir(parents=True)
        (tmp_path / "project.conf").write_text(
            "name: p\nmin-version: 2.0\nelement-path: elements\n"
            f"variables:\n  bga-source-kinds: {declaration}\n")
        return tmp_path

    def test_a_right_side_naming_no_known_kind_raises(self, tmp_path):
        project = self._project_conf(tmp_path, "gerrit=nosuchkind")
        with pytest.raises(RuntimeError, match="gerrit=nosuchkind"):
            _read_bga_source_kind_map(str(project))

    def test_an_entry_with_no_equals_sign_raises(self, tmp_path):
        project = self._project_conf(tmp_path, "gerrit")
        with pytest.raises(RuntimeError, match="gerrit"):
            _read_bga_source_kind_map(str(project))

    def test_a_well_formed_declaration_parses(self, tmp_path):
        project = self._project_conf(tmp_path, "gerrit=git,mirror=tar")
        assert _read_bga_source_kind_map(str(project)) == {
            "gerrit": "git", "mirror": "tar"}


class TestTheCoverageReachesTheCliOutput:
    """The nine tests above build an inventory and call `bga/sources.py`
    directly - never through `bga/cli.py`'s `_attach_resource_blast` or
    `bga/report/json.py`'s publish gate. A verifier hardcoded the
    attached list to `[]`, and separately reverted the gate to
    `if blast.get('rows'):`, and the suite stayed green both times.
    This drives the real CLI so both are exercised.
    """

    def test_an_unmapped_kind_with_no_shared_resource_still_publishes(self, tmp_path):
        run_dir = tmp_path / "run"
        shutil.copytree(REPO_ROOT / "tests/fixtures/with_timeline/run", run_dir)
        sources_path = run_dir / "sources.json"
        inventory = json.loads(sources_path.read_text())
        # One element, one resource, no other element shares it - the
        # coverage naming does not depend on a blast row existing.
        inventory["elements"]["gerrit-only.bst"] = [{
            "kind": "gerrit",
            "identity": "example.com/org/gerrit-only",
            "declared": "example.com/org/gerrit-only",
            "keying": "unknown",
            "staged_at": None,
        }]
        sources_path.write_text(json.dumps(inventory, indent=2))

        env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
        completed = subprocess.run(
            ["python3", "-m", "bga.cli", "analyze", str(run_dir), "--format", "json"],
            cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=60)
        assert completed.returncode == 0, completed.stderr
        document = json.loads(completed.stdout)
        blast = document.get("resource_blast")
        assert blast is not None, sorted(document)
        assert blast["rows"] == []
        assert blast["unmapped_source_kinds"] == ["gerrit"]
