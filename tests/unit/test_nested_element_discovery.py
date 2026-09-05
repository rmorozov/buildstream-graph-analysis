"""UX-160: the census must read the whole element tree, not just its top.

Discovery was `os.listdir(...).endswith(".bst")` in five places, all
non-recursive. Every example in this repository keeps its elements at
the top level, so every test passed; essentially every real project
nests them, and there the census assessed nothing below the top level.

The bill lands through UX-113's fail-safe - an unassessed element is
traced - so `--trace-spine=auto`, snapshot's default, quietly became
`--trace-spine=on` for the whole build.
"""

from tools.bst_native_build_tracer import (
    discover_element_names,
    format_census_coverage,
)
from tools.native_trace.bwrap_shim import element_from_build_root, extract_element_name


def _project(tmp_path, names, element_path=None):
    (tmp_path / "project.conf").write_text(
        "name: x\n" + (f"element-path: {element_path}\n" if element_path else ""))
    root = tmp_path / (element_path or "elements")
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("kind: manual\n")
    return str(tmp_path)


class TestDiscoveryWalksTheWholeTree:
    def test_a_flat_project_is_unchanged(self, tmp_path):
        project = _project(tmp_path, ["core.bst", "app.bst"])
        assert discover_element_names(project) == ["app.bst", "core.bst"]

    def test_nested_elements_are_found(self, tmp_path):
        """The layout `os.listdir` missed entirely."""
        project = _project(tmp_path, ["components/core.bst", "components/app.bst"])
        assert discover_element_names(project) == [
            "components/app.bst", "components/core.bst"]

    def test_names_are_project_relative_not_basenames(self, tmp_path):
        """A basename would collide across directories and would not match
        what BuildStream, Plane 1, or the shim call the element."""
        project = _project(tmp_path, ["a/core.bst", "b/core.bst"])
        assert discover_element_names(project) == ["a/core.bst", "b/core.bst"]

    def test_it_recurses_more_than_one_level(self, tmp_path):
        project = _project(tmp_path, ["a/b/c/deep.bst"])
        assert discover_element_names(project) == ["a/b/c/deep.bst"]

    def test_non_bst_files_are_ignored(self, tmp_path):
        project = _project(tmp_path, ["components/core.bst", "components/README.md"])
        assert discover_element_names(project) == ["components/core.bst"]

    def test_it_honours_a_custom_element_path_and_nesting_together(self, tmp_path):
        """UX-153 routed the directory; UX-160 the walk. Both at once is
        the case neither item covered alone."""
        project = _project(tmp_path, ["components/core.bst"], element_path="src")
        assert discover_element_names(project) == ["components/core.bst"]

    def test_a_missing_element_directory_is_empty_not_an_error(self, tmp_path):
        (tmp_path / "project.conf").write_text("name: x\n")
        assert discover_element_names(str(tmp_path)) == []


class TestTheShimRecoversTheSameName:
    """Item 2, and the reason recursion alone would have been useless.

    Measured on a real nested capture: BuildStream's own generated argv
    carries `--dir buildstream/<project>/components/core.bst`, so the
    old last-segment recovery said `core.bst` while a recursive census
    keys on `components/core.bst`. Every nested element would have
    stayed unassessed, with the census carrying entries nobody reads.
    """

    def test_a_nested_build_root_yields_the_nested_name(self):
        assert element_from_build_root(
            "buildstream/proj/components/core.bst") == "components/core.bst"

    def test_a_flat_build_root_is_unchanged(self):
        assert element_from_build_root("buildstream/proj/core.bst") == "core.bst"

    def test_a_deeply_nested_name_survives_whole(self):
        assert element_from_build_root(
            "buildstream/proj/a/b/c.bst") == "a/b/c.bst"

    def test_a_build_root_override_keeps_the_last_segment(self):
        """UX-56: an overridden build root collapses every element into one
        directory. Inventing structure there would be worse than the flat
        name it already gives."""
        assert element_from_build_root("/buildstream-build") == "buildstream-build"

    def test_it_reads_the_real_option_form(self):
        opts = ["--bind", "/x", "/y", "--dir",
                "buildstream/proj/components/lib-a.bst", "--chdir", "/"]
        assert extract_element_name(opts) == "components/lib-a.bst"

    def test_no_dir_option_still_returns_none(self):
        assert extract_element_name(["--bind", "/x", "/y"]) is None

    def test_the_census_key_and_the_shim_name_agree(self, tmp_path):
        """The property the whole item turns on, asserted directly."""
        project = _project(tmp_path, ["components/core.bst"])
        census_key = discover_element_names(project)[0]
        shim_name = extract_element_name(
            ["--dir", f"buildstream/proj/{census_key}"])
        assert shim_name == census_key


class TestTheCensusOutcomeIsVisible:
    def test_full_coverage_says_so(self, tmp_path):
        project = _project(tmp_path, ["a.bst", "b.bst"])
        line = format_census_coverage(project, {"a.bst": False, "b.bst": True})
        assert "2 of 2 element(s) assessed" in line
        assert "1 with static binaries" in line
        assert "unassessed" not in line

    def test_partial_coverage_names_what_auto_is_really_doing(self, tmp_path):
        """The number that matters: unassessed elements are traced by the
        fail-safe, so a large count means `auto` is `on`."""
        project = _project(tmp_path, ["a.bst", "b.bst", "c.bst"])
        line = format_census_coverage(project, {"a.bst": False})
        assert "1 of 3 element(s) assessed" in line
        assert "2 unassessed" in line
        assert "`auto` is behaving as `on`" in line

    def test_an_empty_census_is_reported_not_hidden(self, tmp_path):
        project = _project(tmp_path, ["a.bst"])
        line = format_census_coverage(project, {})
        assert "0 of 1" in line and "1 unassessed" in line
