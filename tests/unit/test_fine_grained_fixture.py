"""UX-120: the fixture `UX-100`'s acceptance named, checked for shape.

The merge candidate had fired only on synthetic unit-test input. Both
real captures it had ever seen produced the *negative* answer — which is
the correct answer for those projects, and is also exactly what an inert
detector produces. `examples/09-fine-grained-siblings` is the positive
case, and these assert it still has the properties the detector keys on:
eight siblings with one identical build-dependency set, and a `merged/`
variant holding the same translation units in one element.

Shape only — the numbers live in `UX-0120`'s verification log, because
they need a real `bst build` and this tier does not.
"""
import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT = os.path.join(REPO, "examples", "09-fine-grained-siblings")
MERGED = os.path.join(PROJECT, "merged")

_DEPENDS = re.compile(r"^- filename: (\S+)$", re.M)


def _depends(element_path):
    with open(element_path) as handle:
        return sorted(_DEPENDS.findall(handle.read()))


def _siblings():
    return sorted(
        name for name in os.listdir(os.path.join(PROJECT, "elements"))
        if name.startswith("tiny-") and name.endswith(".bst")
    )


def test_there_are_eight_siblings():
    """Two would satisfy the criterion; eight is what makes the deleted
    stagings and the projection worth measuring against a real rebuild."""
    assert len(_siblings()) == 8


def test_every_sibling_declares_the_identical_dependency_set():
    """The detector groups by exact parent set - a merge only makes sense
    where the graph would not notice. One sibling with an extra edge
    silently drops the group below the two-member floor."""
    sets = {tuple(_depends(os.path.join(PROJECT, "elements", name)))
            for name in _siblings()}

    assert len(sets) == 1, sets
    assert sets == {("bulk.bst", "toolchain.bst")}


def test_the_bulk_dependency_is_declared_and_generated_not_committed():
    """60k one-byte files is the whole point and also unshippable: it is
    what makes staging reach the one second BuildStream can report."""
    bulk = os.path.join(PROJECT, "elements", "bulk.bst")

    assert os.path.isfile(bulk)
    assert os.path.isfile(os.path.join(PROJECT, "generate_bulk.py"))

    with open(os.path.join(REPO, ".gitignore")) as handle:
        ignored = handle.read()
    assert "examples/09-fine-grained-siblings/files/bulk/" in ignored


def test_the_generator_makes_enough_files_to_be_measurable():
    """Measured on this fixture: 8k files stage in under a second and the
    toll rounds to 0.00; 60k stage in one and the share reaches 0.50.
    A generator quietly reduced below that would turn the positive case
    back into a negative one, which is the failure this whole task is
    about."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "generate_bulk", os.path.join(PROJECT, "generate_bulk.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.DIRS * module.PER_DIR >= 60_000


def test_the_merged_variant_holds_the_same_units_in_one_element():
    """The projection is checked against this, so it has to be the same
    work - a merged variant that quietly dropped a unit would make the
    merge look cheaper than it is."""
    merged_elements = sorted(
        name for name in os.listdir(os.path.join(MERGED, "elements"))
        if name.startswith("tiny")
    )
    assert merged_elements == ["tiny-merged.bst"]

    sources = sorted(os.listdir(os.path.join(MERGED, "files", "src", "tiny-merged")))
    assert sources == ["CMakeLists.txt"] + [f"tiny-{i}.cpp" for i in range(1, 9)]


def test_the_merged_variant_shares_the_siblings_dependency_set():
    """Merging changes the element count, not what the sandbox stages -
    otherwise the before/after timing would be measuring two things."""
    assert _depends(os.path.join(MERGED, "elements", "tiny-merged.bst")) == \
        _depends(os.path.join(PROJECT, "elements", "tiny-1.bst"))


def test_the_two_projects_do_not_share_a_buildstream_name():
    """Two projects with one name land in one log tree, and Plane 3 reads
    the log tree by project name - the before and after would merge."""
    names = []
    for root in (PROJECT, MERGED):
        with open(os.path.join(root, "project.conf")) as handle:
            match = re.search(r"^name: (\S+)$", handle.read(), re.M)
            assert match, root
            names.append(match.group(1))

    assert names[0] != names[1], names


@pytest.mark.parametrize("root", [PROJECT, MERGED])
def test_each_project_builds_everything_through_one_target(root):
    """`all.bst` is what every capture command in the docs builds; an
    element missing from it is an element the fixture does not exercise."""
    with open(os.path.join(root, "elements", "all.bst")) as handle:
        body = handle.read()
    expected = sorted(
        name for name in os.listdir(os.path.join(root, "elements"))
        if name.startswith("tiny-")
    )
    assert sorted(re.findall(r"^- (tiny-\S+\.bst)$", body, re.M)) == expected
