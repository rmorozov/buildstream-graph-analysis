"""UX-113: the spine and the census, finally introduced.

The census knows, before the build starts and per element, whether the
staged root holds a static executable - i.e. whether the `LD_PRELOAD`
hook will be blind there. The spine was all-or-nothing, priced for every
element to cover the few where it is the only witness. So it stayed
opt-in, and therefore mostly off, which quietly re-opened the blind spot
the whole of Direction 4 closed.
"""
import json
import os

import pytest

from tools.bst_native_build_tracer import census_project, census_spine_verdicts
from tools.native_trace.bwrap_shim import spine_for_element

SPINE = "/dst/spine"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def staged_project(name, *sentinel):
    """An example project, or a skip if its binaries are not on disk.

    The census classifies executables the staging scripts put there, and
    `.gitignore` keeps those out of the repo - so on a fresh checkout
    every verdict below is `False` because there was nothing to
    classify. That is indistinguishable from the regression these tests
    exist to catch, so an unstaged fixture skips rather than passes.
    `bst-tests` runs both staging scripts and then the whole suite, so
    the tier is not skipped everywhere CI looks.
    """
    project = os.path.join(REPO_ROOT, "examples", name)
    if not os.path.isfile(os.path.join(project, *sentinel)):
        pytest.skip(
            "examples/%s is not staged - run examples/stage_runtimes.sh and "
            "examples/stage_cpp_toolchain.sh" % name
        )
    return project


@pytest.fixture
def census(tmp_path):
    path = tmp_path / "spine-census.json"
    path.write_text(json.dumps({"static.bst": True, "dynamic.bst": False}))
    return str(path)


class TestWhichElementsGetTraced:
    def test_an_element_the_hook_is_blind_for_is_traced(self, census):
        assert spine_for_element("auto", census, "static.bst", SPINE) == SPINE

    def test_an_all_dynamic_element_is_not(self, census):
        assert spine_for_element("auto", census, "dynamic.bst", SPINE) is None

    def test_an_element_the_census_never_assessed_is_traced(self, census):
        """"We did not assess it" and "we assessed it and it is clean"
        are different claims, and only one of them is safe to skip."""
        assert spine_for_element("auto", census, "unknown.bst", SPINE) == SPINE

    def test_an_element_whose_name_could_not_be_recovered_is_traced(self, census):
        """Under a build-root override (`UX-56`) that is *every* element,
        so a project which collapses its names gets `on` rather than a
        silently empty policy."""
        assert spine_for_element("auto", census, None, SPINE) == SPINE

    def test_a_missing_census_traces_everything(self, tmp_path):
        """The safe direction for a policy whose whole purpose is to not
        lose coverage."""
        missing = str(tmp_path / "nope.json")
        assert spine_for_element("auto", missing, "static.bst", SPINE) == SPINE
        assert spine_for_element("auto", None, "static.bst", SPINE) == SPINE

    @pytest.mark.parametrize("policy", [None, "on", "off"])
    def test_the_other_policies_are_untouched(self, policy, census):
        """`auto` is a third value of one question, not a rewrite of the
        two that were already there."""
        assert spine_for_element(policy, census, "dynamic.bst", SPINE) == SPINE
        assert spine_for_element(policy, census, "dynamic.bst", None) is None


class TestTheCensusVerdicts:
    def test_a_busybox_project_needs_the_spine_everywhere(self):
        project = staged_project(
            "01-resource-contention", "files", "runtime", "bin", "sh")
        verdicts = census_spine_verdicts(project)

        assert verdicts, "the census produced no verdicts at all"
        assert all(verdicts.values()), "every element here runs static busybox"

    def test_a_glibc_toolchain_needs_it_nowhere(self):
        project = staged_project(
            "06-macro-micro-optimization", "files", "toolchain", "usr", "bin", "gcc")
        verdicts = census_spine_verdicts(project)

        assert verdicts, "the census produced no verdicts at all"
        assert not any(verdicts.values()), verdicts

    def test_the_glibc_verdict_is_a_classification_not_an_empty_shelf(self):
        """`not any(...)` above is also what a census of nothing returns.

        The claim worth pinning is the positive half: the census *found*
        executables in this project and classified every one of them as
        dynamic. Without this, deleting the toolchain would strengthen
        the test above rather than break it.
        """
        project = staged_project(
            "06-macro-micro-optimization", "files", "toolchain", "usr", "bin", "gcc")
        elements = sorted(
            name for name in os.listdir(os.path.join(project, "elements"))
            if name.endswith(".bst")
        )
        toolchain = census_project(project, elements)["per_element"]["toolchain.bst"]

        assert toolchain["dynamic_executables"] > 0, toolchain
        assert toolchain["static_count"] == 0, toolchain

    def test_an_unreadable_project_yields_no_verdicts_rather_than_wrong_ones(self):
        assert census_spine_verdicts("/nonexistent/project") == {}
