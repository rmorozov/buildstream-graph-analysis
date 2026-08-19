"""UX-113: the spine and the census, finally introduced.

The census knows, before the build starts and per element, whether the
staged root holds a static executable - i.e. whether the `LD_PRELOAD`
hook will be blind there. The spine was all-or-nothing, priced for every
element to cover the few where it is the only witness. So it stayed
opt-in, and therefore mostly off, which quietly re-opened the blind spot
the whole of Direction 4 closed.
"""
import json

import pytest

from tools.bst_native_build_tracer import census_spine_verdicts
from tools.native_trace.bwrap_shim import spine_for_element

SPINE = "/dst/spine"


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
        verdicts = census_spine_verdicts("examples/01-resource-contention")

        assert verdicts, "the census produced no verdicts at all"
        assert all(verdicts.values()), "every element here runs static busybox"

    def test_a_glibc_toolchain_needs_it_nowhere(self):
        verdicts = census_spine_verdicts("examples/06-macro-micro-optimization")

        assert verdicts, "the census produced no verdicts at all"
        assert not any(verdicts.values()), verdicts

    def test_an_unreadable_project_yields_no_verdicts_rather_than_wrong_ones(self):
        assert census_spine_verdicts("/nonexistent/project") == {}
