"""UX-1298: `compare/v2` publishes the band's origin and its skipped-for-host count.

`--band-from-class` reads its members from a store or a `--bundles` tree
and may skip members measured on another host; both answers are keys on
the document, and the CI comment's sentence is rendered from them.
"""

import json
import types

from bga import schemas
from bga.exceptions import EXIT_OK
from bga.report.ci_comment import _band_selection
from tests.unit.test_the_band_comes_from_the_class import _compare
from tests.unit.test_the_band_is_drawn_on_the_candidates_host import HOST_A, HOST_B
from tests.unit.test_the_band_is_drawn_on_the_candidates_host import _store as _host_store
from tests.unit.test_the_gate_reads_kept_bundles_in_place import _tree, runner  # noqa: F401

KEYS = ("baseline_band_origin", "baseline_band_skipped_for_host")


def _json(baseline, candidate, *extra) -> dict:
    code, output = _compare(baseline, candidate, *extra, "--format", "json")
    assert code == EXIT_OK, output
    return json.loads(output[output.index("{") :])


class TestCompareNamesWhereItsBandCameFrom:
    def test_a_kept_tree_with_one_member_on_another_host_publishes_both(self, tmp_path, runner):  # noqa: F811
        _work, _scratch, baseline, candidate = runner
        tree = _tree(tmp_path, [HOST_A] * 3 + [HOST_B])

        document = _json(baseline, candidate, "--band-from-class", "--bundles", str(tree))

        assert document["baseline_band_origin"] == {"kind": "bundles", "path": str(tree)}
        assert document["baseline_band_skipped_for_host"] == {"count": 1, "fields": ["cpu_model"]}
        assert len(document["baseline_band_sources"]) == 3

    def test_a_store_band_names_the_store(self, tmp_path):
        baseline, candidate = _host_store(tmp_path, [HOST_A] * 4, baseline_in_members=True)

        document = _json(baseline, candidate, "--band-from-class")

        assert document["baseline_band_origin"] == {"kind": "store", "path": str(tmp_path / "project")}
        assert document["baseline_band_skipped_for_host"] == {"count": 0, "fields": []}

    def test_a_pair_comparison_writes_both_as_null(self, tmp_path):
        baseline, candidate = _host_store(tmp_path, [HOST_A] * 4, baseline_in_members=True)

        document = _json(baseline, candidate)

        assert [document[key] for key in KEYS] == [None, None]
        assert set(KEYS) <= set(schemas.schema(schemas.COMPARE)["bga:always_written"])


class TestTheCommentReadsTheKeys:
    def test_the_sentence_is_rendered_from_the_comparison_alone(self):
        comparison = types.SimpleNamespace(
            baseline_band_origin={"kind": "bundles", "path": "kept/review"},
            baseline_band_skipped_for_host={"count": 2, "fields": ["cpu_model"]},
        )

        assert _band_selection(comparison) == (
            " — read from the bundles under `kept/review` — 2 runs of this class skipped, measured on another host"
        )

    def test_a_store_band_with_nothing_skipped_adds_nothing(self):
        comparison = types.SimpleNamespace(
            baseline_band_origin={"kind": "store", "path": "/p"},
            baseline_band_skipped_for_host={"count": 0, "fields": []},
        )

        assert _band_selection(comparison) == ""
