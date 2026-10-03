"""UX-1330: a short element name the run does not hold is refused with the
junction-qualified element(s) it may mean, never substituted."""

from types import SimpleNamespace

from bga import blast, whatif

QUALIFIED = "junctions/platform.bst:junctions/base.bst:pkgs/gcc-libs.bst"


def _refusal(selected, uids):
    graph = SimpleNamespace(elements=[SimpleNamespace(uid=uid) for uid in uids])
    [refusal] = whatif._refusals(graph, {uid: 1 for uid in uids}, selected)
    return refusal


class TestWhatif:
    def test_one_match_is_named_and_still_refused(self):
        refusal = _refusal(["pkgs/gcc-libs.bst"], [QUALIFIED, "other.bst"])

        assert refusal["check"] == "unknown_element"
        assert f"Did you mean {QUALIFIED}?" in refusal["sentence"]

    def test_every_match_is_named_when_several(self):
        other = "junctions/x.bst:pkgs/gcc-libs.bst"

        sentence = _refusal(["pkgs/gcc-libs.bst"], [QUALIFIED, other])["sentence"]

        assert QUALIFIED in sentence and other in sentence

    def test_no_match_adds_no_suggestion(self):
        assert "Did you mean" not in _refusal(["ghost.bst"], [QUALIFIED])["sentence"]

    def test_a_longer_name_is_not_a_last_component_match(self):
        assert whatif.did_you_mean("gcc-libs.bst", ["pkgs/gcc-libs.bst"]) == []


class TestBlast:
    def test_the_text_names_the_match_where_the_target_reads_as_a_path(self):
        answer = {
            "target": "pkgs/gcc-libs.bst",
            "resolved_as": "path",
            "also_matched": ["element"],
            "direct_count": 0,
            "element_exists": False,
            "has_inventory": True,
            "did_you_mean": [QUALIFIED],
        }

        assert f"Did you mean {QUALIFIED}?" in blast.format_blast_text(answer)

    def test_the_text_names_the_match_where_the_target_reads_as_an_element(self):
        answer = {
            "target": "gcc-libs.bst",
            "resolved_as": "element",
            "also_matched": [],
            "direct_count": 0,
            "element_exists": False,
            "has_inventory": True,
            "did_you_mean": [QUALIFIED],
        }

        assert f"Did you mean {QUALIFIED}?" in blast.format_blast_text(answer)

    def test_the_payload_carries_it_for_a_run_keyed_by_qualified_names(self):
        answer = blast.blast("tests/fixtures/synthetic_multi_subproject", "libcore.bst", measure=False)

        assert answer["did_you_mean"] == ["core-utils.bst:libcore.bst"]
        assert "Did you mean core-utils.bst:libcore.bst?" in blast.format_blast_text(answer)
