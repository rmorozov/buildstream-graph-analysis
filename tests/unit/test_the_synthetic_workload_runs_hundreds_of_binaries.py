"""`UX-1182`: `gen-synthetic --store --workload binaries` runs hundreds of
fake binaries per element, from named distributions, inside each
element's Plane 1 window, byte-identical from one seed - and leaves the
default store and Plane 1 as they were."""

import collections
import gzip
import json
from datetime import datetime, timezone

import pytest

from tests.pages import REVIEW_SHAPE, heavy_binary_run, two_plane_run
from tools.gen_synthetic_scale_run import DISTRIBUTIONS, STORE_STAMP


def _store(into, name, *shape):
    return sorted(two_plane_run(into, shape, name=name).parents[1].iterdir())


def _plane2(snapshot):
    with gzip.open(snapshot / "plane2.log.gz", "rt", encoding="utf-8") as handle:
        return handle.read()


def _field(line, name):
    return line.split(f" {name}=", 1)[1].split(" ", 1)[0]


@pytest.fixture(scope="module")
def stores(tmp_path_factory):
    root = tmp_path_factory.mktemp("workload")
    run = heavy_binary_run(root)
    return {
        "heavy": sorted(run.parents[1].iterdir()),
        "again": _store(root, "again", "--workload", "binaries", *REVIEW_SHAPE),
        "default": _store(root, "default", *REVIEW_SHAPE),
    }


def _distinct(snapshot):
    seen = collections.defaultdict(set)
    for line in _plane2(snapshot).splitlines():
        if line.startswith("START"):
            seen[_field(line, "element")].add(line.split("cmd=", 1)[1].split(" ", 1)[0].rsplit("/", 1)[-1])
    return seen


def test_several_elements_run_hundreds_of_distinct_binaries(stores):
    for snapshot in stores["heavy"]:
        wide = [uid for uid, binaries in _distinct(snapshot).items() if len(binaries) >= 200]
        assert len(wide) >= 5, sorted(len(b) for b in _distinct(snapshot).values())[-8:]


def test_every_named_distribution_is_drawn(stores):
    binaries = set().union(*_distinct(stores["heavy"][-1]).values())
    assert {name for name in DISTRIBUTIONS if any(b.startswith(f"{name}-") for b in binaries)} == set(DISTRIBUTIONS)
    assert len(DISTRIBUTIONS) >= 5


def test_each_binary_draws_from_the_distribution_it_is_named_for(stores):
    walls, modes = collections.defaultdict(list), collections.defaultdict(list)
    for line in _plane2(stores["heavy"][-1]).splitlines():
        if line.startswith("END") and "/opt/fakebin/" in line:
            binary, mode, wall = line.split("cmd=", 1)[1].split(" ")
            walls[binary.rsplit("/", 1)[1].split("-")[0]].append(float(wall))
            burnt = 0.95 * float(wall) if mode == "--burn" else 0.001
            modes[mode].append(abs(float(_field(line, "utime")) - burnt))
    assert set(walls["constant"]) == {0.05}
    assert min(walls["uniform"]) >= 0.01 and max(walls["uniform"]) <= 0.5
    tail = sorted(walls["pareto"])
    assert tail[-1] >= 10 * tail[len(tail) // 2] and tail[0] >= 0.02
    assert all(len(set(walls[name])) > 100 for name in ("uniform", "exponential", "lognormal", "pareto"))
    assert max(modes["--burn"] + modes["--sleep"]) <= 0.0006
    assert min(len(modes["--burn"]), len(modes["--sleep"])) > 100


def test_every_process_lies_inside_its_elements_plane1_window(stores):
    for snapshot in stores["heavy"]:
        epoch = datetime.strptime(snapshot.name, STORE_STAMP).replace(tzinfo=timezone.utc).timestamp()
        with open(snapshot / "run" / "trace.json", encoding="utf-8") as handle:
            spans = json.load(handle)["spans"]
        window = {
            s["task_key"].split("|")[0]: (epoch + s["ts_us"] / 1e6, epoch + (s["ts_us"] + s["dur_us"]) / 1e6)
            for s in spans
        }
        lines = _plane2(snapshot).splitlines()
        assert len(lines) > 2000
        for line in lines:
            begin, end = window[_field(line, "element")]
            assert begin - 1e-6 <= float(_field(line, "ts")) <= end + 1e-6, line


def test_both_planes_join_on_every_building_element(stores):
    snapshot = stores["heavy"][-1]
    with open(snapshot / "plane2.json", encoding="utf-8") as handle:
        report = json.load(handle)
    with open(snapshot / "run" / "graph.json", encoding="utf-8") as handle:
        building = {e["uid"] for e in json.load(handle)["elements"] if e["element_kind"] not in ("import", "stack")}
    starts = _plane2(snapshot).count("START ")
    assert report["process_count"] == report["matched_count"] == starts
    assert set(report["binary_cost"]) == building


def test_one_seed_gives_one_plane2(stores):
    assert [_plane2(s) for s in stores["heavy"]] == [_plane2(s) for s in stores["again"]]


def test_the_workload_moves_plane2_alone(stores):
    assert len(stores["heavy"]) == len(stores["default"])  # zip(strict=) is 3.10+ (UX-1346)
    for heavy, default in zip(stores["heavy"], stores["default"]):
        for name in ("build.log", "run/graph.json", "run/trace.json"):
            assert (heavy / name).read_bytes() == (default / name).read_bytes(), name
        with open(default / "run" / "graph.json", encoding="utf-8") as handle:
            every = sorted(e["uid"] for e in json.load(handle)["elements"])
        starts = [line for line in _plane2(default).splitlines() if line.startswith("START")]
        assert sorted(_field(line, "element") for line in starts) == every
        assert {line.split("cmd=", 1)[1].split(" ", 1)[0] for line in starts} == {"/usr/bin/cc"}
