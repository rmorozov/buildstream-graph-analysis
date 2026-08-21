"""UX-181 and UX-182: what one identity is, and where the inventory stops.

`normalize_url` exists so a blast is not halved by two spellings of one
repository. Round 19 found it failing in both directions - mangling one
repository into two identities, and merging many pip packages into one.
UX-182 is the boundary: the projects the monorepo question comes from
keep most elements behind junctions, so an inventory that stops at the
junction answers "unreadable" on exactly the shape the axis was built
for.
"""
import json
import os
import shutil

import pytest

from bga import sources
from bga.blast import blast, classify_target
from tools.bst_extract_run import build_source_inventory


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO_ROOT, "tests", "fixtures", "golden", "mixed_task_kinds")


class TestOneRepositoryStaysOneIdentity:
    @pytest.mark.parametrize("url", [
        "https://host/org/repo.git",
        "HTTPS://host/org/repo",
        "git+https://host/org/repo.git",
        "git@host:org/repo.git",
        "ssh://git@host/org/repo",
    ])
    def test_every_spelling_of_one_repository_agrees(self, url):
        """UX-181: `git+https` and an uppercase scheme used to come back
        as `git+https///host/org/repo` and `https///Host/Org/Repo` -
        garbage identities, and the halved blast this exists to stop."""
        assert sources.normalize_url(url) == "host/org/repo"

    def test_a_scheme_it_does_not_know_is_returned_untouched(self):
        """Better one identity for one resource than a mangled second."""
        assert sources.normalize_url("weird+scheme://x/y") == "weird+scheme://x/y"

    def test_a_port_is_still_not_a_path(self):
        assert sources.normalize_url("ssh://git@host:2222/org/repo") == \
            "host:2222/org/repo"

    def test_different_repositories_stay_different(self):
        assert sources.normalize_url("https://host/org/one") != \
            sources.normalize_url("https://host/org/two")


class TestPipKeysOnThePackage:
    def test_two_packages_from_one_index_are_two_resources(self):
        """UX-181: keying on the index url made every pip element in a
        project one shared "repository", under the sentence "any commit
        to this rebuilds all of them" - which is not what an index is."""
        first, _ = sources.resource_of_source({
            "kind": "pip", "url": "https://pypi.org/simple",
            "packages": ["requests"]})
        second, _ = sources.resource_of_source({
            "kind": "pip", "url": "https://pypi.org/simple",
            "packages": ["numpy"]})
        assert first["identity"] != second["identity"]
        assert first["identity"].startswith("requests")
        assert second["identity"].startswith("numpy")

    def test_one_package_on_two_indexes_is_two_resources(self):
        """UX-192, the same item's title case pointing the other way:
        UX-181 dropped the index entirely, so a package name published
        on a public index and on an internal mirror collapsed into one
        resource - the over-grouping it was filed to remove."""
        public, _ = sources.resource_of_source({
            "kind": "pip", "url": "https://pypi.org/simple",
            "packages": ["requests"]})
        internal, _ = sources.resource_of_source({
            "kind": "pip", "url": "https://mirror.example.com/simple",
            "packages": ["requests"]})
        assert public["identity"] != internal["identity"]
        # The package still leads, because it is what a reader is
        # looking for; the index disambiguates behind it.
        assert public["identity"].startswith("requests ")
        assert public["declared"] == internal["declared"] == "requests", (
            "`declared` is what the recipe wrote, not what bga composed")

    def test_an_index_less_pip_source_keys_on_the_package_alone(self):
        resource, _ = sources.resource_of_source({
            "kind": "pip", "packages": ["requests"]})
        assert resource["identity"] == "requests"

    def test_the_sentence_comes_from_the_kind(self):
        assert "pinned version" in sources.keying_clause(
            {"kind": "pip", "keying": "ref"})
        assert "any commit" in sources.keying_clause(
            {"kind": "git", "keying": "ref"})
        assert "archive" in sources.keying_clause(
            {"kind": "tar", "keying": "ref"})

    def test_a_pip_source_with_no_packages_is_named_not_grouped(self):
        resource, complaint = sources.resource_of_source({
            "kind": "pip", "url": "https://pypi.org/simple"})
        assert resource is None
        assert "index url is not an identity" in complaint


class TestTheSplitCountsAGeneratorOnce:
    def test_a_generator_does_not_yield_a_negative_count(self):
        """UX-181: the argument was iterated twice, so a generator was
        exhausted by the first pass."""
        kinds = {"a.bst": "manual", "b.bst": "stack"}
        assert sources.split_by_kind((uid for uid in kinds), kinds) == (1, 1)
        assert sources.split_by_kind(list(kinds), kinds) == (1, 1)


class TestTheInventoryWalksIntoCheckedOutJunctions:
    def _project(self, tmp_path, junction_source):
        project = tmp_path / "top"
        (project / "elements").mkdir(parents=True)
        (project / "project.conf").write_text(
            "name: top\nmin-version: 2.0\nelement-path: elements\n")
        (project / "elements" / "sub.bst").write_text(junction_source)

        sub = project / "subproj"
        (sub / "elements").mkdir(parents=True)
        (sub / "project.conf").write_text(
            "name: sub\nmin-version: 2.0\nelement-path: elements\n")
        (sub / "elements" / "libfoo.bst").write_text(
            "kind: manual\nsources:\n- kind: local\n  path: files/libfoo\n")
        (sub / "elements" / "vendored.bst").write_text(
            "kind: manual\nsources:\n- kind: git\n"
            "  url: https://gitlab.example.com/org/monorepo.git\n"
            "  directory: src/foo\n")
        return str(project)

    LOCAL_JUNCTION = "kind: junction\nsources:\n- kind: local\n  path: subproj\n"

    def test_a_local_junction_is_walked_into(self, tmp_path):
        project = self._project(tmp_path, self.LOCAL_JUNCTION)
        inventory = build_source_inventory(project, ["sub.bst:libfoo.bst"])
        assert inventory["unreadable"] == {}
        assert inventory["elements"]["sub.bst:libfoo.bst"][0]["identity"] == \
            "sub.bst:files/libfoo"

    def test_a_content_identity_is_namespaced_to_its_junction(self, tmp_path):
        """`files/libfoo` means a different directory in each project."""
        project = self._project(tmp_path, self.LOCAL_JUNCTION)
        (tmp_path / "top" / "elements" / "own.bst").write_text(
            "kind: manual\nsources:\n- kind: local\n  path: files/libfoo\n")
        inventory = build_source_inventory(
            project, ["own.bst", "sub.bst:libfoo.bst"])
        identities = {uid: resources[0]["identity"]
                      for uid, resources in inventory["elements"].items()}
        assert identities["own.bst"] == "files/libfoo"
        assert identities["sub.bst:libfoo.bst"] == "sub.bst:files/libfoo"

    def test_a_repository_url_crosses_the_boundary_unchanged(self, tmp_path):
        """The whole point of the axis: two projects sourcing one
        monorepo must group, whichever side of a junction they sit."""
        project = self._project(tmp_path, self.LOCAL_JUNCTION)
        (tmp_path / "top" / "elements" / "top-vendored.bst").write_text(
            "kind: manual\nsources:\n- kind: git\n"
            "  url: https://gitlab.example.com/org/monorepo.git\n"
            "  directory: src/top\n")
        inventory = build_source_inventory(
            project, ["top-vendored.bst", "sub.bst:vendored.bst"])
        grouped = sources.elements_by_resource(inventory)
        assert grouped[("git", "gitlab.example.com/org/monorepo")] == \
            ["sub.bst:vendored.bst", "top-vendored.bst"]

    def test_an_unfetched_junction_is_named(self, tmp_path):
        project = self._project(
            tmp_path,
            "kind: junction\nsources:\n- kind: git\n  url: https://host/sub.git\n")
        inventory = build_source_inventory(project, ["sub.bst:libfoo.bst"])
        assert "sub.bst:libfoo.bst" not in inventory["elements"]
        assert "not checked out here" in \
            " ".join(inventory["unreadable"]["sub.bst:libfoo.bst"])

    def test_a_nested_junction_resolves_left_to_right(self, tmp_path):
        project = self._project(tmp_path, self.LOCAL_JUNCTION)
        sub = tmp_path / "top" / "subproj"
        (sub / "elements" / "deeper.bst").write_text(
            "kind: junction\nsources:\n- kind: local\n  path: deeper\n")
        deeper = sub / "deeper"
        (deeper / "elements").mkdir(parents=True)
        (deeper / "project.conf").write_text(
            "name: deeper\nmin-version: 2.0\nelement-path: elements\n")
        (deeper / "elements" / "leaf.bst").write_text(
            "kind: manual\nsources:\n- kind: local\n  path: files/leaf\n")
        inventory = build_source_inventory(
            project, ["sub.bst:deeper.bst:leaf.bst"])
        assert inventory["elements"]["sub.bst:deeper.bst:leaf.bst"][0]["identity"] \
            == "sub.bst:deeper.bst:files/leaf"


class TestTheCheapAnswer:
    def _run(self, tmp_path):
        run = tmp_path / "run"
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        (run / "sources.json").write_text(json.dumps(sources.build_inventory({
            "lib.bst": [{"kind": "local", "identity": "files/lib",
                         "declared": "files/lib", "keying": "content",
                         "staged_at": None}],
        })))
        return run

    def test_the_structure_is_answered_without_the_analysis(self, tmp_path):
        """UX-182: a lookup should not cost a full analysis."""
        run = self._run(tmp_path)
        cheap = blast(run, "base.bst", project_dir=str(tmp_path), measure=False)
        full = blast(run, "base.bst", project_dir=str(tmp_path))
        assert cheap["blast_elements"] == full["blast_elements"]
        assert cheap["building_count"] == full["building_count"]
        assert cheap["measured"] is False and full["measured"] is True

    def test_it_says_the_cost_was_not_measured_rather_than_unmeasured(self, tmp_path):
        from bga.blast import format_blast_text

        run = self._run(tmp_path)
        text = format_blast_text(
            blast(run, "base.bst", project_dir=str(tmp_path), measure=False))
        assert "Cost: not measured" in text
        assert "no element of the blast ran" not in text

    def test_the_analysis_pipeline_is_never_entered(self, tmp_path, monkeypatch):
        """The saving, not the sentence about it.

        The wording keys on the flag, so it would keep reading right
        with the expensive half still running - which is the whole cost
        this exists to avoid on a project of thousands of elements.
        """
        from bga import blast as blast_module

        def refuse(*_args, **_kwargs):
            raise AssertionError("--no-cost ran the full analysis anyway")

        monkeypatch.setattr(blast_module, "_tasks_of", refuse)
        run = self._run(tmp_path)
        answer = blast_module.blast(run, "base.bst", project_dir=str(tmp_path),
                                    measure=False)
        assert answer["blast_count"] >= 1


class TestPathsResolveFromWhereYouAre:
    def _run(self, tmp_path):
        run = tmp_path / "run"
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        (run / "sources.json").write_text(json.dumps(sources.build_inventory({
            "lib.bst": [{"kind": "local", "identity": "components/lib",
                         "declared": "components/lib", "keying": "content",
                         "staged_at": None}],
        })))
        return run

    def test_a_project_relative_path_still_works(self, tmp_path):
        run = self._run(tmp_path)
        answer = blast(run, "components/lib/main.c", project_dir=str(tmp_path),
                       measure=False)
        assert answer["direct_elements"] == ["lib.bst"]

    def test_an_absolute_path_resolves_against_the_project(self, tmp_path):
        """UX-182 item 3: typed from a subdirectory, or pasted from an
        editor - both arrive absolute."""
        run = self._run(tmp_path)
        absolute = str(tmp_path / "components" / "lib" / "main.c")
        answer = blast(run, absolute, project_dir=str(tmp_path), measure=False)
        assert answer["direct_elements"] == ["lib.bst"]

    def test_a_path_typed_from_a_subdirectory_finds_what_the_root_form_finds(
            self, tmp_path, monkeypatch):
        """UX-182 item 3, the case the item was actually filed about: the
        developer is `cd`'d into the component they just edited and types
        the file's name as their shell completes it. Answering "rebuilds
        nothing" there is the same confident false negative UX-178 closed
        one reading over."""
        run = self._run(tmp_path)
        here = tmp_path / "components" / "lib"
        here.mkdir(parents=True)
        (here / "main.c").write_text("int main(void) { return 0; }\n")
        monkeypatch.chdir(here)

        from_root = blast(run, "components/lib/main.c", project_dir=str(tmp_path),
                          measure=False)
        from_here = blast(run, "main.c", project_dir=str(tmp_path), measure=False)
        assert from_here["direct_elements"] == from_root["direct_elements"] == ["lib.bst"]

    def test_a_shell_standing_outside_the_project_is_not_consulted(
            self, tmp_path, monkeypatch):
        """The other half of the same rule. `main.c` beside a shell that
        is nowhere near this project says nothing about what the project
        stages, and reading it as a path would trade one confident wrong
        answer for another."""
        run = self._run(tmp_path)
        elsewhere = tmp_path.parent / (tmp_path.name + "-elsewhere")
        elsewhere.mkdir()
        (elsewhere / "main.c").write_text("unrelated\n")
        monkeypatch.chdir(elsewhere)

        assert "path" not in classify_target("main.c", str(tmp_path), {})
        answer = blast(run, "main.c", project_dir=str(tmp_path), measure=False)
        assert answer["direct_elements"] == []
        assert answer["resolved_as"] != "path", (
            "a file beside an unrelated shell was read as a path in this project")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
