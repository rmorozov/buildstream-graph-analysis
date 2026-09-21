"""`UX-907`: what an element's artifact weighs, and never a proxy for it.

`UX-896` closed the host-level half and filed this one because
BuildStream 2.8.0 publishes no per-element figure. The one key that
looks like it, `%{artifact-cas-digest}`, renders the root `Directory`
proto's own length: on a real cache that reads 165x to 530,682x under
the artifact, and not monotonically, so a ranking built on it inverts.

So the numbers here come from a walk of a real CAS -
`tests/fixtures/cas_artifact`, written by `buildbox-casd` from the
BuildStream 2.8.0 wheel - and every one of them is the sum of the
proto sizes its README prints. What is guarded is the arithmetic *and*
the honesty of the name: an element's weight is what it would need in
an empty cache, the rows therefore overlap, and the block and the
sentence both have to say so rather than quietly publishing a sum that
is not the cache's content.
"""
import pathlib

import pytest

from bga import artifact_weight
from bga.cache_effectiveness import compute_artifact_weights
from bga.findings import _artifact_weight_findings

FIXTURE = str(pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "cas_artifact")

#: The fixture's own keys, and one element that has no artifact in it.
BASE = "b1a5e0000000000000000000000000000000000000000000000000000000cafe"
APP = "a99f00000000000000000000000000000000000000000000000000000000beef"
ELEMENTS = [("base.bst", BASE), ("app.bst", APP), ("missing.bst", "0" * 64)]

#: Hand-checkable against the README: 78+155+162+5+86+23 and
#: 78+154+77+45+86+23. `tool-alias` is `tool`'s blob, counted once.
BASE_BYTES = 509
APP_BYTES = 463
#: `libshared.so` (23) and the `usr/lib` proto holding it (86), in both.
SHARED_BYTES = 109


@pytest.fixture(scope="module")
def walked():
    return artifact_weight.weigh_elements(FIXTURE, "lab", ELEMENTS)


class TestTheWalkReadsARealCache:
    def test_an_artifact_weighs_what_its_blobs_weigh(self, walked):
        rows = walked["elements"]
        assert rows["base.bst"]["files_bytes"] == BASE_BYTES
        assert rows["app.bst"]["files_bytes"] == APP_BYTES

    def test_a_file_staged_twice_is_counted_once(self, walked):
        """`tool` and `tool-alias` are one 5-byte blob under two names.
        A walk that summed file *nodes* rather than distinct blobs
        would read 514, and would grow with every hardlink a recipe
        makes rather than with what the cache holds."""
        assert walked["elements"]["base.bst"]["files_bytes"] == BASE_BYTES < 514

    def test_the_rows_overlap_and_the_total_does_not(self, walked):
        """The claim the name has to carry. Each artifact holds all 109
        shared bytes because each would need them alone; the cache holds
        them once."""
        rows = walked["elements"]
        total = rows["base.bst"]["files_bytes"] + rows["app.bst"]["files_bytes"]
        assert total == 972
        assert walked["run_unique_bytes"] == total - SHARED_BYTES == 863

    def test_an_element_with_no_artifact_says_so(self, walked):
        """Not zero. A cache miss, a failure and an eviction all reach
        here, and none of them is an artifact that weighs nothing."""
        row = walked["elements"]["missing.bst"]
        assert row["source"] == "ref_absent"
        assert row["files_bytes"] is None

    def test_the_walk_reads_one_blob_per_directory_and_none_per_file(self, walked):
        """The cost claim behind choosing this over `bst artifact
        list-contents`: four directories each, eight reads, six files."""
        assert walked["walk_dirs_read"] == 8

    def test_an_element_with_no_cache_key_is_not_looked_up(self):
        keyless = artifact_weight.weigh_elements(FIXTURE, "lab", [("x.bst", None)])
        assert keyless["elements"]["x.bst"]["source"] == "ref_absent"
        assert keyless["walk_dirs_read"] == 0

    def test_a_half_evicted_tree_refuses_the_sum(self, tmp_path):
        """A truncated sum is not a weight. The root proto is there and
        the subtree it names is not, which is what an eviction between
        `bst build` and the walk leaves behind."""
        import shutil
        cache = tmp_path / "cache"
        shutil.copytree(FIXTURE, cache)
        # `usr/` under `base` - b397bacc..., the one subdirectory its
        # root names, so the root still parses and the tree does not.
        shutil.rmtree(cache / "cas" / "objects" / "b3")
        out = artifact_weight.weigh_elements(str(cache), "lab", [("base.bst", BASE)])
        assert out["elements"]["base.bst"]["source"] == "incomplete"
        assert out["elements"]["base.bst"]["files_bytes"] is None

    def test_the_budget_refuses_rather_than_truncates(self):
        out = artifact_weight.weigh_elements(FIXTURE, "lab", ELEMENTS, budget_s=-1.0)
        assert out["elements"]["base.bst"]["source"] == "budget_exceeded"
        assert out["elements"]["base.bst"]["files_bytes"] is None

    def test_the_ref_path_is_the_one_buildstream_writes(self):
        """`<cachedir>/artifacts/refs/<project>/<normal_name>/<key>`,
        with the element name normalised as `element.py:3440,3456` does
        it - the suffix dropped, separators to `-`, the rest to `_`."""
        assert artifact_weight.normal_name("base/thing.bst") == "base-thing"
        assert artifact_weight.normal_name("a+b.bst") == "a_b"
        assert artifact_weight.ref_path("/c", "p", "sub/e.bst", "k") == (
            "/c/artifacts/refs/p/sub-e/k")


class _Ctx:
    def __init__(self, artifact_weights=None):
        self.artifact_weights = artifact_weights


class TestTheBlockSaysWhatTheNumberIs:
    def test_the_block_ranks_and_states_the_overlap(self, walked):
        block = compute_artifact_weights(_Ctx(walked))
        assert [row["element"] for row in block["heaviest"]] == ["base.bst", "app.bst"]
        assert block["walked_bytes"] == 972
        assert block["run_unique_bytes"] == 863
        assert block["shared_bytes"] == SHARED_BYTES
        assert block["elements_walked"] == 2
        assert block["elements_unweighed"] == 1
        assert block["source"] == "cas_walk"

    def test_nothing_walked_publishes_nothing(self):
        """Not a block of zeros: a capture taken without
        `--artifact-weights` looked at no cache at all."""
        assert compute_artifact_weights(_Ctx(None)) == {}
        assert compute_artifact_weights(_Ctx(
            {"elements": {"a.bst": {"source": "ref_absent"}}})) == {}

    def test_the_sentence_says_the_number_is_walked(self, walked):
        finding = _artifact_weight_findings(compute_artifact_weights(_Ctx(walked)))[0]
        assert finding["id"] == "artifact-weight"
        assert "base.bst" in finding["title"]
        assert "walked from the CAS" in finding["title"]

    def test_the_sentence_says_the_rows_overlap(self, walked):
        """The acceptance test's own clause. A reader who adds the rows
        up has to be told, in the report, that the sum is not the
        cache's content."""
        finding = _artifact_weight_findings(compute_artifact_weights(_Ctx(walked)))[0]
        overlap = [line for line in finding["detail"] if "more than one artifact" in line]
        assert overlap, finding["detail"]
        assert "863" in overlap[0] or "863 B" in overlap[0]

    def test_no_sentence_without_a_walk(self):
        assert _artifact_weight_findings({}) == []
