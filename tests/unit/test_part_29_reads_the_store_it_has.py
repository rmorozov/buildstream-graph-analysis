"""UX-565: Part 29 was wired to `None` while the store held its series.

`bga/analyzer.py` passed `historical_durations=None` unconditionally,
so `compute_duration_variability` returned `[]` on every run bga has
ever analysed - including the ones whose store already held three
same-host captures with a per-element duration slice each (`UX-226`).
Measured on a planted store of three runs scaled 1.0 / 1.6 / 2.4
before this landed:

```text
diag.duration_variability: []
elements keys: blast_radius, blast_radius_ranked_by,
               criticality_probability, downstream_count,
               element_durations, slack, top_blast_radius,
               unweighted_depth, zero_slack_share
duration_variability in document: False
```

The samples are the store's earlier snapshots of **this run's host
class** plus this run's own measured durations. Its own, rather than
its slice, because `bga snapshot` analyses before it writes the slice -
so a series read from the store alone would hold one fewer sample at
capture time than on any later `bga analyze` of the same snapshot.
`test_the_sample_count_does_not_depend_on_when_it_is_asked` is that
property.
"""
import json
import os
import pathlib
import shutil

import pytest

from bga import schemas, store_aggregate
from bga.analyzer import BuildEfficiencyAnalyzer
from bga.compare import MIN_BASELINE_RUNS
from bga.report.json import build_document
from bga.tools_dispatch import _import_tool

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

FAST_HOST = {"schema": "host/v1", "cpu_model": "Ryzen 9 7950X",
             "cpu_count": 32, "memory_mb": 64000}
SLOW_HOST = {"schema": "host/v1", "cpu_model": "Xeon E5-2680",
             "cpu_count": 16, "memory_mb": 32000}


def _plant(tmp_path, runs, slices=True):
    """A store whose snapshots are the golden run scaled `(scale, host)`.

    The trace is rescaled and the slice written by the real
    `write_element_slice`, so what the reader here reads is what the
    capture actually writes rather than a hand-made file.
    """
    (tmp_path / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    snapshot = _import_tool("tools.bga_snapshot")
    planted = []
    for index, (scale, host) in enumerate(runs, start=1):
        snap = tmp_path / ".bga" / "runs" / f"2026{index:02d}01T000000Z"
        run = snap / "run"
        snap.mkdir(parents=True, exist_ok=True)
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        context = json.loads((run / "run-context.json").read_text())
        context["host_manifest"] = dict(host)
        (run / "run-context.json").write_text(json.dumps(context))
        trace = json.loads((run / "trace.json").read_text())
        cursor = 0
        for span in trace.get("spans") or []:
            span["dur_us"] = int(span["dur_us"] * scale)
            span["ts_us"] = cursor
            cursor += span["dur_us"]
        (run / "trace.json").write_text(json.dumps(trace))
        if slices:
            assert snapshot.write_element_slice(str(snap), str(run))
        planted.append(run)
    return planted


def _variability(run):
    result = BuildEfficiencyAnalyzer().analyze(pathlib.Path(run))
    document = build_document(result)
    return (document.get("elements") or {}).get("duration_variability")


class TestTheStoreIsThePartTwentyNineHistory:
    def test_three_same_host_runs_publish_a_non_empty_block(self, tmp_path):
        """The Acceptance Test. Scales 1.0/1.6/2.4 on a 6000us element
        give 6000/9600/14400 -> mean 10000, and the coefficient of
        variation is hand-computable from those three."""
        runs = _plant(tmp_path, [(1.0, FAST_HOST), (1.6, FAST_HOST),
                                 (2.4, FAST_HOST)])
        block = _variability(runs[-1])
        assert block, "Part 29 published nothing on a store that has a history"
        row = block["base.bst"]
        assert row["samples"] == 3
        assert row["mean_us"] == pytest.approx(10000.0)
        assert row["median_us"] == 10000
        assert row["p95_us"] == 14000
        # sqrt(((6000-10000)^2 + 0 + (14000-10000)^2) / 3) / 10000
        assert row["coefficient_of_variation"] == pytest.approx(0.32659863, abs=1e-7)
        assert row["high_variability"] is True

    def test_a_run_outside_a_store_still_has_no_history(self):
        """The golden fixture is a bare run directory. Nothing invents
        a series for it, and the key is simply absent."""
        assert _variability(GOLDEN) is None

    def test_the_other_machines_runs_are_not_samples(self, tmp_path):
        """`UX-186`, which `UX-565` is explicitly not allowed to
        suspend: two of these three ran on a different host, so this
        run's class has one sample and the floor refuses it."""
        runs = _plant(tmp_path, [(1.0, SLOW_HOST), (1.6, SLOW_HOST),
                                 (2.4, FAST_HOST)])
        assert _variability(runs[-1]) is None
        # And the same three runs on one machine do publish - so the
        # refusal above is the host class and not the fixture.
        other = tmp_path / "same"
        other.mkdir()
        same = _plant(other, [(1.0, FAST_HOST), (1.6, FAST_HOST),
                              (2.4, FAST_HOST)])
        assert _variability(same[-1])

    def test_every_row_names_the_machine_its_samples_came_from(self, tmp_path):
        """A sample count with no host class is a figure a reader
        cannot check the refusal above against."""
        runs = _plant(tmp_path, [(1.0, FAST_HOST), (1.6, FAST_HOST),
                                 (2.4, FAST_HOST)])
        classes = {row["host_class"] for row in _variability(runs[-1]).values()}
        assert len(classes) == 1
        assert "Ryzen 9 7950X" in classes.pop()

    def test_two_runs_are_below_the_floor(self, tmp_path):
        """`MIN_BASELINE_RUNS`, the floor `distribution` already
        refuses under - a spread over two runs is two numbers wearing
        a statistic's name."""
        assert MIN_BASELINE_RUNS == 3
        runs = _plant(tmp_path, [(1.0, FAST_HOST), (1.6, FAST_HOST)])
        assert _variability(runs[-1]) is None

    def test_the_sample_count_does_not_depend_on_when_it_is_asked(
            self, tmp_path):
        """`bga snapshot` analyses (`tools/bga_snapshot.py:543`) before
        it writes this snapshot's slice (`:548`). Reading this run's
        own sample from the store would therefore give the capture's
        `analyze.json` one fewer sample than a later `bga analyze` of
        the same directory - two documents about one run."""
        runs = _plant(tmp_path, [(1.0, FAST_HOST), (1.6, FAST_HOST),
                                 (2.4, FAST_HOST)])
        after = _variability(runs[-1])
        os.remove(runs[-1].parent / "element-slice.json")
        during = _variability(runs[-1])
        assert during == after


class TestTheHistoryReaderItself:
    def test_a_directory_that_is_not_a_snapshot_run_has_none(self, tmp_path):
        for path in (None, "", str(tmp_path), str(GOLDEN)):
            assert store_aggregate._snapshot_of(path) is None

    def test_the_window_is_the_one_the_sparkline_draws(self):
        """The card's history line and the figure beside it must not be
        about different runs."""
        source = (REPO / "bga/viewer/element.js").read_text(encoding="utf-8")
        drawn = int(source.split("HISTORY_POINTS_MAX = ", 1)[1].split(";", 1)[0])
        assert drawn == store_aggregate.HISTORY_RUNS_MAX


class TestTheDocumentDeclaresIt:
    def test_it_is_element_keyed_and_optional_rather_than_universal(self):
        """`ELEMENT_KEYED` is the maps *every* run carries, and the
        guards on it read it that way. This one needs a store."""
        assert "duration_variability" not in schemas.ELEMENT_KEYED
        assert "duration_variability" in schemas.ELEMENT_KEYED_OPTIONAL
        assert "duration_variability" in schemas.ELEMENT_POPULATION

    def test_the_published_fields_are_declared(self, tmp_path):
        """`UX-343`: a member with no node renders from the viewer's
        name-sniff. Every field this publishes has one."""
        runs = _plant(tmp_path, [(1.0, FAST_HOST), (1.6, FAST_HOST),
                                 (2.4, FAST_HOST)])
        published = set(next(iter(_variability(runs[-1]).values())))
        declared = set(schemas._ANALYZE_HINTS["elements"]["properties"]
                       ["duration_variability"]["additionalProperties"]
                       ["properties"])
        assert published == declared

    def test_the_card_draws_it(self):
        source = (REPO / "bga/viewer/element.js").read_text(encoding="utf-8")
        maps = source.split("const ELEMENT_MAPS = [", 1)[1].split("];", 1)[0]
        assert "elements.duration_variability" in maps
        assert "coefficient_of_variation" in maps


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
