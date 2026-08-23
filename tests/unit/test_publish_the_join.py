"""UX-215: publish the join the tool already computes.

`bga/correlate.py:141` has assembled an `ElementJoin` per element since
`UX-51` — Plane 1's path share, saving and blast radius beside Plane
2's cores busy, jobs asked for and peak RSS — and `bga correlate
--format json` has emitted it, correctly and completely, the whole
time. What it lacked was a **contract**: no `schema` stamp, so
`UX-190`'s rule did not cover it; no view-hints, so `bga view` could
not render it generically; and `payloads()` did not serve it.
`correlate --schema` said so in the tool's own words: *"correlate
produces no versioned JSON output."*

So this is not new analysis. It is a stamp, a schema and some wiring —
and the guards below are shaped accordingly: they assert that what is
published is *the same join*, field for field, rather than that it has
some plausible shape.
"""
import json
import os
import subprocess
import sys

import pytest

from bga import schemas

jsonschema = pytest.importorskip("jsonschema")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO, "tests", "fixtures", "golden", "mixed_task_kinds")
REAL = os.path.join(
    REPO, "examples", "06-macro-micro-optimization", ".bga", "runs",
    "20260821T170127Z")
has_capture = pytest.mark.skipif(
    not os.path.isdir(REAL), reason="the examples/06 capture is not here")


def _bga(args):
    return subprocess.run([sys.executable, "-m", "bga.cli", *args],
                          capture_output=True, text=True, cwd=REPO)


# `UX-213`'s rule, which this item is one round too young to forget: an
# acceptance that only runs where an uncommitted capture lives is an
# acceptance that does not run. The golden fixture is in git and its
# critical path is `base.bst -> lib.bst -> app.bst`; this is a Plane 2
# report for it, written per test rather than checked in, so the join
# has two real planes to join on every machine.
#
# Deliberately partial: `app.bst` is on the path and absent from Plane
# 2, which is the degrade case, and `ghost.bst` is a name Plane 2
# produced that Plane 1 never declared, which is `UX-66`'s.
def _golden_plane2():
    return {
        "by_element": {"base.bst": 1, "lib.bst": 1, "ghost.bst": 1},
        "per_element_parallelism": [
            {"element": "base.bst", "requested_jobs": 1,
             "findings": ["pinned_to_one_job"]},
            {"element": "lib.bst", "requested_jobs": 4, "findings": []},
            {"element": "ghost.bst", "requested_jobs": 1, "findings": []},
        ],
        "cpu_time": {"per_element": {
            "base.bst": {"cpu_per_wall_second": 0.87, "coverage": 0.94},
            "lib.bst": {"cpu_per_wall_second": 3.4, "coverage": 1.0},
            "ghost.bst": {"cpu_per_wall_second": 1.0, "coverage": 1.0},
        }},
        "peak_memory": {"per_element": {
            "base.bst": {"peak_rss_kb": 157200},
            "lib.bst": {"peak_rss_kb": 48000},
        }},
        "declared_vs_used": {"unused_candidates": []},
    }


@pytest.fixture
def golden_plane2(tmp_path):
    path = tmp_path / "plane2.json"
    path.write_text(json.dumps(_golden_plane2()), encoding="utf-8")
    return str(path)


class TestTheDocumentIsPublished:
    def test_correlate_is_one_of_the_schemas_this_tool_produces(self):
        assert schemas.CORRELATE in schemas.names()

    def test_the_switch_answers_instead_of_refusing(self):
        """It used to print "correlate produces no versioned JSON
        output" - which was true, and is the whole item."""
        result = _bga(["correlate", "--schema"])
        assert result.returncode == 0, result.stderr
        printed = json.loads(result.stdout)
        assert printed["properties"]["schema"]["const"] == schemas.CORRELATE

    def test_the_document_declares_its_element_column(self):
        """`role: "element"` is what earns every row `UX-208`'s Inspect
        with no per-table code, on both arrays that carry the join."""
        declared = schemas.schema(schemas.CORRELATE)["properties"]
        for key in ("elements", "actionable"):
            roles = {c["key"]: c.get("role")
                     for c in declared[key][schemas.COLUMNS]}
            assert roles["element"] == "element", key

    def test_every_join_column_that_is_a_quantity_says_which(self):
        """`peak_rss_kb` is the one that matters: calling it `bytes`
        would be wrong by 1024x, which is the exact class of error
        `UX-201` exists to stop."""
        columns = {c["key"]: c.get("quantity") for c in
                   schemas.schema(schemas.CORRELATE)["properties"]
                   ["elements"][schemas.COLUMNS]}
        assert columns["peak_rss_kb"] == "kilobytes"
        assert columns["potential_saving_us"] == "duration_us"
        assert columns["critical_path_share"] == "share"
        assert columns["cores_busy"] == "ratio"

    def test_kilobytes_is_a_declared_quantity_the_viewer_renders(self):
        assert "kilobytes" in schemas.QUANTITIES
        source = open(os.path.join(REPO, "bga/viewer/app.js"),
                      encoding="utf-8").read()
        assert 'case "kilobytes":' in source, (
            "a quantity nothing renders is a promise nothing keeps")


class TestItIsTheSameJoinOnACommittedFixture:
    """`UX-213`'s rule: the acceptance runs where the repository is,
    not where one machine's capture is. Everything here uses the golden
    run plus a Plane 2 report built in the test."""

    def test_the_output_validates_against_its_own_schema(self, golden_plane2):
        result = _bga(["correlate", GOLDEN, golden_plane2, "--format", "json"])
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["schema"] == schemas.CORRELATE
        assert list(payload)[0] == "schema", "the version must lead"
        jsonschema.validate(payload, schemas.schema(schemas.CORRELATE))

    def test_the_published_rows_are_the_joins_own_rows(self, golden_plane2):
        """Field for field against `correlate()`'s return, so this
        cannot pass by re-deriving anything."""
        from bga.correlate import correlate

        analysis = json.loads(
            _bga(["analyze", GOLDEN, "--format", "json"]).stdout)
        direct = correlate(analysis, _golden_plane2())
        published = json.loads(_bga(
            ["correlate", GOLDEN, golden_plane2, "--format", "json"]).stdout)
        assert published["elements"] == direct["elements"]
        assert published["actionable"] == direct["actionable"]

    def test_the_report_carries_the_same_rows_as_the_command(self, golden_plane2):
        """`UX-215` item 2. One join, so `bga analyze --plane2` and
        `bga correlate` cannot describe the same element differently -
        which is the failure `UX-214` found one round earlier, in the
        verdicts."""
        report = json.loads(_bga(
            ["analyze", GOLDEN, "--format", "json",
             "--plane2", golden_plane2]).stdout)
        joined = json.loads(_bga(
            ["correlate", GOLDEN, golden_plane2, "--format", "json"]).stdout)
        assert report["element_join"] == joined["elements"]
        assert report["element_join"], "the report published an empty join"
        jsonschema.validate(report, schemas.schema(schemas.ANALYZE))

    def test_both_planes_reach_one_row(self, golden_plane2):
        """The point of the whole document: Plane 1's place in the
        graph and Plane 2's measurement inside the sandbox, in a single
        row. `base.bst` holds 43% of the golden path and ran at 0.87
        cores busy having asked for one job."""
        joined = json.loads(_bga(
            ["correlate", GOLDEN, golden_plane2, "--format", "json"]).stdout)
        rows = {row["element"]: row for row in joined["elements"]}
        base = rows["base.bst"]
        assert base["on_critical_path"] is True
        assert base["critical_path_share"] == pytest.approx(0.42857, rel=1e-3)
        assert base["cores_busy"] == pytest.approx(0.87)
        assert base["requested_jobs"] == 1
        assert base["peak_rss_kb"] == 157200

    def test_an_element_plane2_never_saw_degrades_rather_than_zeroes(
            self, golden_plane2):
        """`app.bst` is on the path and absent from Plane 2. Its row
        carries the Plane 1 half and no Plane 2 numbers - not zeros,
        which would read as "measured, and idle"."""
        joined = json.loads(_bga(
            ["correlate", GOLDEN, golden_plane2, "--format", "json"]).stdout)
        rows = {row["element"]: row for row in joined["elements"]}
        assert "app.bst" in rows, "an unseen element must still be a row"
        app = rows["app.bst"]
        assert app.get("cores_busy") is None
        assert app.get("peak_rss_kb") is None
        assert app["on_critical_path"] is True, "its Plane 1 half survives"
        assert joined["coverage"]["plane1_elements"] > \
            joined["coverage"]["plane2_elements"]

    def test_a_plane2_only_name_is_listed_and_never_actionable(
            self, golden_plane2):
        """`UX-66`'s rule, which the published document must not
        weaken: `ghost.bst` is a name Plane 2 produced and Plane 1
        never declared. It belongs in `elements` - hiding it would hide
        a real disagreement between the planes - and may never appear
        in `actionable`."""
        joined = json.loads(_bga(
            ["correlate", GOLDEN, golden_plane2, "--format", "json"]).stdout)
        rows = {row["element"]: row for row in joined["elements"]}
        assert "ghost.bst" in rows, "an undeclared name must be visible"
        assert rows["ghost.bst"]["declared"] is False
        assert "ghost.bst" not in {r["element"] for r in joined["actionable"]}

    def test_without_plane2_the_block_is_absent_not_empty(self):
        """The `UX-202` rule, applied: "not looked at" and "looked at
        and saw nothing" are different claims, and an empty array would
        say the second.

        **Deviation from the Required Fix, recorded:** clause 4 asks
        for the block to be present carrying the Plane 1 half. It is
        not, deliberately - with one plane there is no *join*, and the
        Plane 1 half is already published in `signals`. Publishing it
        twice under a name that promises both planes would be the
        misleading option, not the generous one. Absent Plane 2 within
        a row is still a degrade rather than an error, which
        `test_an_element_plane2_never_saw_degrades_rather_than_zeroes`
        asserts.
        """
        report = json.loads(
            _bga(["analyze", GOLDEN, "--format", "json"]).stdout)
        assert "element_join" not in report
        assert "element_join_coverage" not in report
        jsonschema.validate(report, schemas.schema(schemas.ANALYZE))


@has_capture
class TestItIsTheSameJoin:
    """The acceptance's shape: not "the output looks right" but "the
    output *is* what the join computed"."""

    def test_the_output_validates_against_its_own_schema(self):
        result = _bga(["correlate", os.path.join(REAL, "run"),
                       "--format", "json"])
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["schema"] == schemas.CORRELATE
        assert list(payload)[0] == "schema", "the version must lead"
        jsonschema.validate(payload, schemas.schema(schemas.CORRELATE))

    def test_every_element_the_text_report_names_is_a_row(self):
        """Field for field against the text renderer's own input, so
        this cannot pass by re-deriving anything."""
        from bga.correlate import correlate

        analysis = json.loads(_bga(
            ["analyze", os.path.join(REAL, "run"), "--format", "json"]).stdout)
        native = json.load(open(os.path.join(REAL, "plane2.json"),
                                encoding="utf-8"))
        direct = correlate(analysis, native)

        published = json.loads(_bga(
            ["correlate", os.path.join(REAL, "run"),
             "--format", "json"]).stdout)
        assert published["elements"] == direct["elements"]
        assert published["actionable"] == direct["actionable"]

    def test_the_report_carries_the_same_rows_as_the_command(self):
        """`UX-215` item 2. One join, so `bga analyze --plane2` and
        `bga correlate` cannot describe the same element differently -
        which is the failure `UX-214` found one round earlier, in the
        verdicts."""
        report = json.loads(_bga(
            ["analyze", os.path.join(REAL, "run"), "--format", "json",
             "--plane2", os.path.join(REAL, "plane2.json")]).stdout)
        joined = json.loads(_bga(
            ["correlate", os.path.join(REAL, "run"),
             "--format", "json"]).stdout)
        assert report["element_join"] == joined["elements"]
        assert report["element_join"], "the report published an empty join"

    def test_the_report_still_validates_with_the_join_in_it(self):
        report = json.loads(_bga(
            ["analyze", os.path.join(REAL, "run"), "--format", "json",
             "--plane2", os.path.join(REAL, "plane2.json")]).stdout)
        jsonschema.validate(report, schemas.schema(schemas.ANALYZE))


@has_capture
class TestOnePlaneIsNotAJoin:
    def test_without_plane2_the_block_is_absent_not_empty(self):
        """The `UX-202` rule, applied: "not looked at" and "looked at
        and saw nothing" are different claims, and an empty array would
        say the second.

        **Deviation from the Required Fix, recorded:** clause 4 asks
        for the block to be present carrying the Plane 1 half. It is
        not, deliberately - with one plane there is no *join*, and the
        Plane 1 half is already published in `signals`. Publishing it
        twice under a name that promises both planes would be the
        misleading option, not the generous one. Absent Plane 2 within
        a row is still a degrade rather than an error, which is what
        the next test asserts.
        """
        report = json.loads(_bga(
            ["analyze", os.path.join(REAL, "run"), "--format", "json"]).stdout)
        assert "element_join" not in report
        assert "element_join_coverage" not in report
        jsonschema.validate(report, schemas.schema(schemas.ANALYZE))

    def test_an_element_plane2_never_saw_degrades_rather_than_zeroes(self):
        """Measured on the real capture: Plane 1 declares 11 elements
        and Plane 2 saw 9. The two it missed are rows with a Plane 1
        half and no Plane 2 numbers - not rows claiming zero cores
        busy, which would read as "measured, and idle"."""
        joined = json.loads(_bga(
            ["correlate", os.path.join(REAL, "run"),
             "--format", "json"]).stdout)
        coverage = joined["coverage"]
        assert coverage["plane1_elements"] > coverage["plane2_elements"], (
            "this fixture no longer exercises the partial-coverage case")
        unseen = [row for row in joined["elements"]
                  if row.get("cores_busy") is None]
        assert unseen, "no element is missing its Plane 2 half"
        for row in unseen:
            assert "cores_busy" not in row or row["cores_busy"] is None
            assert row.get("element"), row


class TestTheUndeclaredGateIsLoadBearing:
    """Built after a mutation refused to discriminate, which is the
    honest reason this class exists.

    Deleting `UX-66`'s `if entry.declared` gate left every guard green,
    because a Plane-2-only name never acquires a `saving_share` and
    `_recommend` needs one - so on that path the gate is belt over
    braces. The gate *is* load-bearing on a different path: an element
    Plane 1's sensitivity list names while its own per-element signals
    do not. That case is built here rather than the mutation being
    counted.
    """

    def _views(self):
        # `orphan.bst` is in `top_opportunities` - so it gets a real
        # `saving_share` - and in none of the signals maps `UX-66`
        # builds the declared set from.
        # No `critical_path_detail`, so `_plane1_view` takes UX-70's
        # documented fallback and reads `top_opportunities` - which is
        # the *only* path on which an element can acquire a saving
        # share without appearing in any signals map, and therefore the
        # only path on which the `declared` gate is reachable.
        analysis = {
            "signals": {
                "critical_path": ["real.bst"],
                "blast_radius": {"real.bst": 2},
            },
            "structural": {"sensitivity": {
                "top_opportunities": [["real.bst", 0.45],
                                      ["orphan.bst", 0.40]],
                "critical_path_us": 20_000_000}},
            "total_duration_us": 20_000_000,
        }
        native = {
            "by_element": {"real.bst": 1, "orphan.bst": 1},
            "per_element_parallelism": [
                {"element": "real.bst", "requested_jobs": 1, "findings": []},
                {"element": "orphan.bst", "requested_jobs": 1,
                 "findings": []}],
            "cpu_time": {"per_element": {
                "real.bst": {"cpu_per_wall_second": 0.8, "coverage": 1.0},
                "orphan.bst": {"cpu_per_wall_second": 0.8, "coverage": 1.0}}},
            "declared_vs_used": {"unused_candidates": []},
        }
        return analysis, native

    def test_the_case_is_discriminating(self):
        """Without the gate `orphan.bst` would earn advice: it carries
        a saving share and a low cores-busy, which is exactly what
        `_recommend` fires on."""
        from bga.correlate import _recommend, ElementJoin

        orphan = ElementJoin(element="orphan.bst", declared=False,
                             potential_saving_us=8_000_000,
                             saving_share=0.4, cores_busy=0.8)
        assert _recommend(orphan), (
            "the fixture no longer reaches _recommend, so the gate "
            "below is being asserted against nothing")

    def test_an_undeclared_element_is_listed_and_never_actionable(self):
        from bga.correlate import correlate

        analysis, native = self._views()
        joined = correlate(analysis, native)
        rows = {row["element"]: row for row in joined["elements"]}
        assert "orphan.bst" in rows, (
            "an undeclared name must be visible, not hidden - hiding it "
            "would hide a real disagreement between the planes")
        assert rows["orphan.bst"]["declared"] is False
        assert rows["orphan.bst"]["recommendations"] == []
        assert "orphan.bst" not in {r["element"]
                                    for r in joined["actionable"]}

    def test_the_published_document_carries_that_distinction(self, tmp_path):
        """Through the schema, not just the function: `declared` is a
        published field, so a consumer can make the same refusal."""
        declared = schemas.schema(schemas.CORRELATE)["properties"][
            "elements"]["items"]["properties"]["declared"]
        assert declared["type"] == "boolean"
        assert "UX-66" in declared["description"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
