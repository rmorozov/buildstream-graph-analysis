"""UX-234: the store speaks for more than one build.

Direction 9's anchor. A store of captures **is** a measured
service-time distribution with host manifests, hit rates and resource
profiles attached, and until this its only cross-run reading was a
trend line of medians. "What does a build cost", "how much does it
vary", "what is the p95" - the fact-base for every capacity answer, and
none of it published.

The percentiles here are checked against hand-computed values on a
fixture built for the purpose, because a percentile whose definition is
not pinned is not reproducible - and the two honesty rules the item
inherits are checked as behaviour, not as prose: an unfinished capture
is not a sample, and a mix of machines is not a distribution.
"""
import json
import os
import shutil

import pytest

from bga import schemas, store_aggregate
from bga.compare import MIN_BASELINE_RUNS

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"

FAST_HOST = {"schema": "host/v1", "cpu_model": "Ryzen 9 7950X",
             "cpu_count": 32, "memory_mb": 64000}
SLOW_HOST = {"schema": "host/v1", "cpu_model": "Xeon E5-2680",
             "cpu_count": 16, "memory_mb": 32000}


def _store(tmp_path, runs):
    """A project whose store holds `runs` - `(seconds, host, broken)`."""
    (tmp_path / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    for index, spec in enumerate(runs, start=1):
        seconds, host = spec[0], spec[1]
        broken = spec[2] if len(spec) > 2 else None
        run = tmp_path / ".bga" / "runs" / f"2026{index:02d}01T000000Z" / "run"
        run.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        context = json.loads((run / "run-context.json").read_text())
        context["wall_clock"] = {"start_us": 0, "end_us": int(seconds * 1e6)}
        if host is not None:
            context["host_manifest"] = dict(host)
        if broken == "interrupted":
            context["build_outcome"] = dict(
                context.get("build_outcome") or {}, interrupted=True)
        elif broken == "no_duration":
            context.pop("wall_clock", None)
        (run / "run-context.json").write_text(json.dumps(context))
    return str(tmp_path)


def _aggregate(tmp_path, runs, blend=False):
    return store_aggregate.read(_store(tmp_path, runs), blend=blend)


class TestThePercentilesAreReproducible:
    """Nearest-rank, stated and checked - a percentile without its
    definition is a number nobody can re-derive."""

    def test_the_rank_is_the_one_the_contract_names(self):
        samples = list(range(1, 21))          # 1..20
        # ceil(0.95 * 20) = 19, so the p95 is the 19th value.
        assert store_aggregate.percentile(samples, 95) == 19
        assert store_aggregate.percentile(samples, 50) == 10
        assert store_aggregate.percentile(samples, 100) == 20

    def test_no_interpolation_invents_a_duration_nobody_measured(self):
        samples = [10, 20, 30]
        assert store_aggregate.percentile(samples, 95) in samples

    def test_a_hand_computed_distribution_matches_exactly(self, tmp_path):
        durations = [10, 12, 14, 30, 11]
        document = _aggregate(tmp_path, [(d, FAST_HOST) for d in durations])
        shape = document["host_classes"][0]["duration_us"]
        # sorted: 10 11 12 14 30 -> median 12, ceil(.95*5)=5 -> p95 30
        # deviations from 12: 2 1 0 2 18 -> sorted 0 1 2 2 18 -> MAD 2
        assert shape["min"] == 10_000_000
        assert shape["median"] == 12_000_000
        assert shape["p95"] == 30_000_000
        assert shape["max"] == 30_000_000
        assert shape["mad"] == 2_000_000
        assert shape["samples"] == 5

    def test_below_the_floor_there_is_no_distribution_and_it_says_so(
            self, tmp_path):
        """`MIN_BASELINE_RUNS`, the same floor the noise band refuses
        under: a p95 of two samples is the larger of the two wearing a
        statistic's name."""
        document = _aggregate(tmp_path, [(10, FAST_HOST), (12, FAST_HOST)])
        entry = document["host_classes"][0]
        assert entry["duration_us"] is None
        assert entry["shortfall"]["have"] == 2
        assert entry["shortfall"]["need"] == MIN_BASELINE_RUNS
        assert str(MIN_BASELINE_RUNS) in entry["shortfall"]["sentence"]


class TestAnUnfinishedRunIsNotASample:
    """UX-156's rule, one document up: "we had nine runs" and "we had
    nine and threw two away" are different claims."""

    def test_incomplete_captures_are_excluded_from_the_distribution(
            self, tmp_path):
        runs = [(10, FAST_HOST), (12, FAST_HOST), (14, FAST_HOST),
                (900, FAST_HOST, "interrupted")]
        document = _aggregate(tmp_path, runs)
        shape = document["host_classes"][0]["duration_us"]
        assert shape["samples"] == 3
        assert shape["max"] == 14_000_000, (
            "the interrupted run's 900s reached the distribution")

    def test_they_are_counted_where_they_were_dropped(self, tmp_path):
        runs = [(10, FAST_HOST), (12, FAST_HOST), (14, FAST_HOST),
                (900, FAST_HOST, "interrupted"),
                (0, FAST_HOST, "no_duration")]
        document = _aggregate(tmp_path, runs)
        assert document["snapshots"] == 5
        assert document["measured"] == 3
        assert document["excluded"]["count"] == 2
        assert sum(document["excluded"]["by_reason"].values()) == 2
        assert "no recorded duration" in document["excluded"]["by_reason"]

    def test_the_text_names_the_exclusions(self, tmp_path):
        document = _aggregate(tmp_path, [
            (10, FAST_HOST), (12, FAST_HOST), (14, FAST_HOST),
            (900, FAST_HOST, "interrupted")])
        rendered = "\n".join(store_aggregate.render(document))
        assert "1 excluded" in rendered


class TestAMixOfMachinesIsNotADistribution:
    """UX-186's grammar. Durations are not scaled across hosts, so a
    blended figure is a claim the tool declines to make on its own."""

    MIXED = [(10, FAST_HOST), (12, FAST_HOST), (14, FAST_HOST),
             (50, SLOW_HOST), (55, SLOW_HOST), (60, SLOW_HOST)]

    def test_each_class_aggregates_on_its_own(self, tmp_path):
        document = _aggregate(tmp_path, self.MIXED)
        by_label = {e["host_class"]: e for e in document["host_classes"]}
        assert len(by_label) == 2
        medians = sorted(e["duration_us"]["median"] for e in by_label.values())
        assert medians == [12_000_000, 55_000_000]

    def test_the_blended_number_is_refused_and_the_refusal_names_why(
            self, tmp_path):
        document = _aggregate(tmp_path, self.MIXED)
        assert document["blended"] is None
        assert document["refusal"]["check"] == "cross_host_aggregate"
        assert document["refusal"]["classes"] == 2
        assert "--blend" in document["refusal"]["sentence"]
        assert "Ryzen 9 7950X" in document["refusal"]["sentence"]

    def test_blend_states_the_claim_and_says_how_many_it_mixed(
            self, tmp_path):
        document = _aggregate(tmp_path, self.MIXED, blend=True)
        assert document["blended"]["mixes"] == 2
        # sorted: 10 12 14 50 55 60 -> median (14+50)/2 = 32
        assert document["blended"]["duration_us"]["median"] == 32_000_000
        assert document["refusal"], "the refusal is still recorded"

    def test_one_class_is_not_a_mix_so_nothing_is_refused(self, tmp_path):
        document = _aggregate(tmp_path, [
            (10, FAST_HOST), (12, FAST_HOST), (14, FAST_HOST)])
        assert document["refusal"] is None
        assert document["blended"]["mixes"] == 1

    def test_a_capture_with_no_manifest_is_its_own_class(self, tmp_path):
        """"We do not know which machine" is not "the same machine as
        the others" - merging them would be the blend, silently."""
        document = _aggregate(tmp_path, [
            (10, FAST_HOST), (12, FAST_HOST), (14, FAST_HOST), (11, None)])
        labels = {e["host_class"] for e in document["host_classes"]}
        assert store_aggregate.UNKNOWN_HOST_CLASS in labels

    def test_the_grouping_walks_the_fields_compare_refuses_on(self):
        """One definition of "the same machine". A field added to
        `hostinfo.COMPARED_FIELDS` must widen this grouping too, or the
        aggregate and `bga compare` disagree about it."""
        from bga import hostinfo

        base = {"cpu_model": "m", "cpu_count": 4, "memory_mb": 8}
        for field in hostinfo.COMPARED_FIELDS:
            other = dict(base, **{field: "different"})
            assert store_aggregate.host_class(base) != \
                store_aggregate.host_class(other), field


class TestTheCliAndTheContract:
    def test_the_document_validates_against_its_own_schema(self, tmp_path):
        jsonschema = pytest.importorskip("jsonschema")

        document = _aggregate(tmp_path, [
            (10, FAST_HOST), (12, FAST_HOST), (14, FAST_HOST),
            (50, SLOW_HOST), (55, SLOW_HOST), (60, SLOW_HOST),
            (900, FAST_HOST, "interrupted")])
        jsonschema.validate(document, schemas.schema(schemas.STORE_AGGREGATE))
        assert document["schema"] == schemas.STORE_AGGREGATE

    def test_the_schema_is_registered_where_schemas_are_listed(self):
        assert schemas.STORE_AGGREGATE in schemas.names()

    def test_a_mixed_store_exits_with_the_refusal_code(self, tmp_path, capsys):
        """The same exit code `bga compare` refuses a cross-host pair
        with, because it is the same refusal."""
        from bga.cli import EXIT_CODE_MISMATCHED_RUNS
        from tools.bga_snapshot import main

        project = _store(tmp_path, [
            (10, FAST_HOST), (12, FAST_HOST), (14, FAST_HOST),
            (50, SLOW_HOST), (55, SLOW_HOST), (60, SLOW_HOST)])
        code = main(["--project", project, "--aggregate"])
        assert code == EXIT_CODE_MISMATCHED_RUNS
        assert "--blend" in capsys.readouterr().out

    def test_blend_makes_it_exit_zero(self, tmp_path):
        from tools.bga_snapshot import main

        project = _store(tmp_path, [
            (10, FAST_HOST), (12, FAST_HOST), (14, FAST_HOST),
            (50, SLOW_HOST), (55, SLOW_HOST), (60, SLOW_HOST)])
        assert main(["--project", project, "--aggregate", "--blend"]) == 0

    def test_a_single_class_store_exits_zero(self, tmp_path):
        from tools.bga_snapshot import main

        project = _store(tmp_path, [(10, FAST_HOST), (12, FAST_HOST),
                                    (14, FAST_HOST)])
        assert main(["--project", project, "--aggregate"]) == 0

    def test_the_json_and_the_text_read_the_same_document(
            self, tmp_path, capsys):
        from tools.bga_snapshot import main

        project = _store(tmp_path, [(10, FAST_HOST), (12, FAST_HOST),
                                    (14, FAST_HOST)])
        main(["--project", project, "--aggregate", "--format", "json"])
        document = json.loads(capsys.readouterr().out)
        main(["--project", project, "--aggregate"])
        text = capsys.readouterr().out
        median = document["host_classes"][0]["duration_us"]["median"] / 1e6
        assert f"median {median:.1f}s" in text

    def test_the_listing_carries_each_snapshots_host_class(self, tmp_path):
        from tools.bga_snapshot import store_listing

        project = _store(tmp_path, [(10, FAST_HOST), (50, SLOW_HOST)])
        rows = store_listing(project)["snapshots"]
        assert {row["host_class"] for row in rows} == {
            store_aggregate.host_class(FAST_HOST),
            store_aggregate.host_class(SLOW_HOST)}


class TestTheTrendDrawsThePublishedBand:
    """`renderTrend` gains the band the distribution implies - and
    draws none over a mix, because one band across two machines is the
    blend the aggregate refuses."""

    def _node(self, script):
        import shutil as _shutil
        import subprocess

        node = _shutil.which("node")
        if node is None:
            pytest.skip("node is not installed")
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True,
                                cwd=os.getcwd(), timeout=60)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_the_band_edges_are_the_published_figures(self, tmp_path):
        document = _aggregate(tmp_path, [(10, FAST_HOST), (12, FAST_HOST),
                                         (14, FAST_HOST)])
        out = self._node(_HARNESS.replace("__AGGREGATE__",
                                          json.dumps(document)))
        shape = document["blended"]["duration_us"]
        assert out["band"] == {"median": str(shape["median"]),
                               "p95": str(shape["p95"])}
        assert out["median_line"] == str(shape["median"])

    def test_a_mixed_store_draws_no_band_and_says_why(self, tmp_path):
        document = _aggregate(tmp_path, [
            (10, FAST_HOST), (12, FAST_HOST), (14, FAST_HOST),
            (50, SLOW_HOST), (55, SLOW_HOST), (60, SLOW_HOST)])
        out = self._node(_HARNESS.replace("__AGGREGATE__",
                                          json.dumps(document)))
        assert out["band"] is None
        assert out["note"] == document["refusal"]["sentence"]
        assert out["note_kind"] == "refused"

    def test_no_aggregate_draws_the_trend_it_always_did(self):
        out = self._node(_HARNESS.replace("__AGGREGATE__", "null"))
        assert out["band"] is None and out["note"] is None
        assert out["points"] == 3, "the trend itself stopped rendering"


_HARNESS = """
function make(tag) {
  return {
    tagName: tag, nodeType: 1, attrs: {}, children: [], textContent: "",
    className: "", listeners: {},
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return this.attrs[k] ?? null; },
    append(...xs) { for (const x of xs) { if (x == null) continue;
      typeof x === "string" ? this.textContent += x : this.children.push(x); } },
  };
}
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        getElementById: () => null };
const views = await import("./bga/viewer/views.js");
const store = { schema: "store/v1", snapshots: [
  { stamp: "a", total_duration_us: 10000000 },
  { stamp: "b", total_duration_us: 12000000 },
  { stamp: "c", total_duration_us: 14000000 },
]};
const node = views.renderTrend(store, undefined, __AGGREGATE__);
let band = null, medianLine = null, note = null, noteKind = null, points = 0;
(function walk(n) {
  if (!n) return;
  if (n.attrs["data-band"]) {
    band = { median: n.attrs["data-median"], p95: n.attrs["data-p95"] };
  } else if (n.attrs["data-median"] !== undefined) {
    medianLine = n.attrs["data-median"];
  }
  if (n.attrs["data-distribution"]) {
    note = n.textContent; noteKind = n.attrs["data-distribution"];
  }
  if (n.attrs["data-points"]) points = Number(n.attrs["data-points"]);
  (n.children ?? []).forEach(walk);
})(node);
console.log(JSON.stringify({ band, median_line: medianLine, note,
                             note_kind: noteKind, points }));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
