"""UX-184: paths the inventory read and then quietly got wrong.

Field feedback: *"when analyzing blast radius for repos there is a case
when recipe authors put actual path to repo inside kind:import and
kind:manual — generally there can be special handling needed; maybe we
need to recheck that such cases are handled well."*

Round 20 ground-truthed the checkable half. The inventory **does** read
sources on every element kind - `resources_from_element` never consults
`kind:` - so an `import` or `manual` element with an ordinary source
stanza was always covered. What was not covered is what those recipes
tend to contain: a path pointing somewhere the project does not own.

Two shapes, both of which `bst` itself rejects
(`node_get_project_path` raises LoadError) and both of which the
inventory silently normalised into something else:

- `/opt/monorepo` became the identity `opt/monorepo`, colliding with a
  genuine project-relative `opt/monorepo`;
- `../monorepo` was kept verbatim, and `_elements_for_path`'s fallback
  could still prefix-match it.

And one that is legal and was reported twice: a symlinked source
directory, which halves the blast the table exists to show.
"""
import json
import os
import shutil

import pytest

from bga import sources
from bga.blast import blast

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"


class TestEveryElementKindIsRead:
    """The half round 20 verified as already working, pinned so it stays
    that way - the inventory must not learn to consult `kind:`."""

    @pytest.mark.parametrize("kind", ["import", "manual", "stack", "filter", "script"])
    def test_sources_are_read_whatever_the_element_kind(self, kind):
        resources, complaints = sources.resources_from_element({
            "kind": kind,
            "sources": [{"kind": "git", "url": "https://host/org/repo.git",
                         "ref": "a" * 40}],
        })
        assert not complaints
        assert [r["identity"] for r in resources] == ["host/org/repo"]

    def test_an_import_element_with_a_local_path_is_read(self):
        """The field's own shape: "actual path to repo inside
        kind:import"."""
        resources, _ = sources.resources_from_element({
            "kind": "import",
            "sources": [{"kind": "local", "path": "vendor/monorepo"}],
        })
        assert [r["identity"] for r in resources] == ["vendor/monorepo"]
        assert resources[0]["keying"] == "content"


class TestAPathThisProjectCannotKeyIsNamed:
    def test_an_absolute_path_is_a_complaint_not_an_identity(self):
        resource, complaint = sources.resource_of_source(
            {"kind": "local", "path": "/opt/monorepo"})
        assert resource is None
        assert "absolute" in complaint
        assert "/opt/monorepo" in complaint

    def test_it_does_not_collide_with_a_real_project_relative_path(self):
        """The specific harm: `.strip("/")` turned `/opt/monorepo` into
        `opt/monorepo`, which is a directory a project could really
        have - so two unrelated things merged into one row."""
        inside, _ = sources.resource_of_source(
            {"kind": "local", "path": "opt/monorepo"})
        outside, complaint = sources.resource_of_source(
            {"kind": "local", "path": "/opt/monorepo"})
        assert inside["identity"] == "opt/monorepo"
        assert outside is None and complaint

    def test_an_escaping_path_is_a_complaint(self):
        resource, complaint = sources.resource_of_source(
            {"kind": "local", "path": "../monorepo"})
        assert resource is None
        assert "escapes the project" in complaint

    def test_a_path_that_only_looks_like_it_escapes_is_kept(self):
        """`sub/../files/src` stays inside; refusing it would be the
        over-refusal this check has to avoid."""
        resource, complaint = sources.resource_of_source(
            {"kind": "local", "path": "sub/../files/src"})
        assert complaint is None
        assert resource["identity"] == "files/src", (
            "and normalised, so it is one identity with `files/src`")

    def test_the_complaint_reaches_the_inventory(self):
        resources, complaints = sources.resources_from_element({
            "kind": "manual",
            "sources": [{"kind": "local", "path": "/opt/monorepo"},
                        {"kind": "local", "path": "files/src"}],
        })
        assert [r["identity"] for r in resources] == ["files/src"]
        assert len(complaints) == 1, "the unkeyable stanza was dropped silently"

    def test_a_ref_keyed_absolute_path_is_untouched(self):
        """`git` against a bare repository on local disk is a real and
        legal thing, and its url is an absolute path. The check is for
        *content* keying, where a path is a project-relative identity;
        applying it to a url would refuse a working configuration."""
        resource, complaint = sources.resource_of_source(
            {"kind": "git", "url": "/srv/git/repo.git", "ref": "a" * 40})
        assert complaint is None, "a ref-keyed absolute url was refused"
        assert resource["identity"] == "/srv/git/repo"


class TestTheQueryRefusesThemToo:
    def _run(self, tmp_path, elements):
        run = tmp_path / "run"
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        (run / "sources.json").write_text(json.dumps(sources.build_inventory(elements)))
        return run

    def test_an_old_inventorys_escaping_identity_matches_nothing(self, tmp_path):
        """A `sources.json` written before the complaint existed still
        carries `../monorepo`. It must not prefix-match a query and
        answer confidently about a path this project cannot key."""
        run = self._run(tmp_path, {
            "lib.bst": [{"kind": "local", "identity": "../monorepo",
                         "declared": "../monorepo", "keying": "content",
                         "staged_at": None}],
        })
        answer = blast(run, "../monorepo/src/main.c", project_dir=str(tmp_path),
                       measure=False)
        assert answer["direct_elements"] == []

    def test_a_normal_path_still_matches(self, tmp_path):
        run = self._run(tmp_path, {
            "lib.bst": [{"kind": "local", "identity": "files/src",
                         "declared": "files/src", "keying": "content",
                         "staged_at": None}],
        })
        answer = blast(run, "files/src/main.c", project_dir=str(tmp_path),
                       measure=False)
        assert answer["direct_elements"] == ["lib.bst"]


class TestASymlinkedDirectoryIsOneResource:
    def _project(self, tmp_path):
        project = tmp_path / "project"
        (project / "files" / "lib").mkdir(parents=True)
        (project / "files" / "lib" / "main.c").write_text("int main(void){return 0;}\n")
        (project / "vendor").mkdir()
        os.symlink("../files/lib", project / "vendor" / "lib")
        return project

    def test_two_spellings_of_one_directory_collapse(self, tmp_path):
        from tools.bst_extract_run import _resolve_symlinked

        project = self._project(tmp_path)
        declared = [
            {"kind": "local", "identity": "files/lib", "declared": "files/lib",
             "keying": "content", "staged_at": None},
            {"kind": "local", "identity": "vendor/lib", "declared": "vendor/lib",
             "keying": "content", "staged_at": None},
        ]
        resolved, notes = _resolve_symlinked(str(project), declared)
        assert not notes
        assert {r["identity"] for r in resolved} == {"files/lib"}, (
            "a symlinked staging directory halved the blast it exists to show")
        assert [r["declared"] for r in resolved] == ["files/lib", "vendor/lib"], (
            "`declared` keeps what the recipe wrote")

    def test_a_link_out_of_the_project_is_named(self, tmp_path):
        from tools.bst_extract_run import _resolve_symlinked

        project = self._project(tmp_path)
        outside = tmp_path / "outside"
        outside.mkdir()
        os.symlink(outside, project / "escape")
        resolved, notes = _resolve_symlinked(str(project), [
            {"kind": "local", "identity": "escape", "declared": "escape",
             "keying": "content", "staged_at": None}])
        assert resolved == []
        assert len(notes) == 1 and "outside the project" in notes[0]

    def test_a_ref_keyed_resource_is_left_alone(self, tmp_path):
        from tools.bst_extract_run import _resolve_symlinked

        declared = [{"kind": "git", "identity": "host/org/repo",
                     "declared": "https://host/org/repo.git", "keying": "ref",
                     "staged_at": None}]
        resolved, notes = _resolve_symlinked(str(self._project(tmp_path)), declared)
        assert resolved == declared and not notes

    def test_a_path_not_on_disk_keeps_its_declared_identity(self, tmp_path):
        """Extracting against a tree that no longer has the directory -
        the identity is still the best answer available, and inventing
        one would be worse."""
        from tools.bst_extract_run import _resolve_symlinked

        resolved, notes = _resolve_symlinked(str(self._project(tmp_path)), [
            {"kind": "local", "identity": "files/gone", "declared": "files/gone",
             "keying": "content", "staged_at": None}])
        assert [r["identity"] for r in resolved] == ["files/gone"]
        assert not notes


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
