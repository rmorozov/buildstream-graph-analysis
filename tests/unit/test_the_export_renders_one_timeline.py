"""UX-1081: `export`'s degradation ladder counts a step's tracks from
the run before rendering it, instead of rendering to find out - 7.2s of
two full renders on the 5,002-element store, one of them thrown away
(the audit).
"""
import gzip
import json
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.unit.test_the_export_degrades_before_it_refuses import _snapshot
from tools import bga_view as view
from tools.bga_timeline import PLANE1_ONLY, render


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory):
    return _snapshot(tmp_path_factory.mktemp("predict"))


def test_predicted_tracks_matches_the_1202_element_store(tmp_path_factory):
    """`UX-430`'s own scale run, 1,202 elements: the acceptance's named
    fixture, at both narrowing steps."""
    snap = pages.scale_two_plane_snapshot(
        tmp_path_factory.mktemp("scale1202"), per_element=3)
    scratch = tmp_path_factory.mktemp("scale1202-render")
    whole = render(str(snap), str(scratch / "whole.pftrace"), quiet=True)
    plane1 = render(str(snap), str(scratch / "plane1.pftrace"), quiet=True,
                    planes=PLANE1_ONLY)

    run = str(snap / "run")
    assert view.predicted_tracks(run) == whole["tracks"]
    assert view.predicted_tracks(run, planes=PLANE1_ONLY) == plane1["tracks"]


def test_predicted_tracks_equals_the_rendered_count(snapshot, tmp_path):
    """The prediction is exact, not a curve fit - on both narrowing
    steps of a small fixture where we still render to check it."""
    whole = render(str(snapshot), str(tmp_path / "whole.pftrace"), quiet=True)
    plane1 = render(str(snapshot), str(tmp_path / "plane1.pftrace"),
                    quiet=True, planes=PLANE1_ONLY)

    assert view.predicted_tracks(str(snapshot / "run")) == whole["tracks"]
    assert view.predicted_tracks(str(snapshot / "run"),
                                 planes=PLANE1_ONLY) == plane1["tracks"]


def test_export_renders_once_when_the_first_step_is_over_budget(
        snapshot, tmp_path, monkeypatch):
    """The 5,002-element shape: the first step is over the track
    ceiling, so it is never rendered - only the step that fits is."""
    whole = render(str(snapshot), str(tmp_path / "probe.pftrace"), quiet=True)
    plane1 = render(str(snapshot), str(tmp_path / "probe1.pftrace"),
                    quiet=True, planes=PLANE1_ONLY)
    assert plane1["tracks"] < whole["tracks"]
    monkeypatch.setattr(view, "TRACE_TRACK_BUDGET", plane1["tracks"])

    calls = []
    real = view.trace_with_planes

    def counting(run, planes=None):
        calls.append(planes)
        return real(run, planes=planes)

    monkeypatch.setattr(view, "trace_with_planes", counting)

    path = tmp_path / "report.html"
    view.export(str(snapshot / "run"), str(path))

    assert len(calls) == 1, (
        f"expected exactly one trace_with_planes call, got {calls}")
    payload = json.loads(re.search(
        r'id="bga-run">(.*?)</script>',
        path.read_text(encoding="utf-8"), re.S).group(1))
    assert payload["trace_planes"] == ["1"]
    said = payload["timeline_degraded"]
    assert "--planes 1" in said, said
    assert f"{whole['tracks']:,} tracks" in said, (
        f"the page does not say what the whole timeline would have "
        f"drawn, from the skipped step's counted tracks: {said}")


def test_a_fixture_over_the_byte_ceiling_only_still_renders_twice(
        snapshot, tmp_path, monkeypatch):
    """The pre-check is track-only; the byte ceiling is still only
    knowable after a render, so that path keeps its second render."""
    calls = []
    real = view.trace_with_planes

    def counting(run, planes=None):
        calls.append(planes)
        return real(run, planes=planes)

    monkeypatch.setattr(view, "trace_with_planes", counting)
    monkeypatch.setattr(view, "TRACE_BUDGET_B", 1)

    path = tmp_path / "report.html"
    view.export(str(snapshot / "run"), str(path))

    assert len(calls) == 2, calls
    payload = json.loads(re.search(
        r'id="bga-run">(.*?)</script>',
        path.read_text(encoding="utf-8"), re.S).group(1))
    assert payload["has_timeline"] is False
    assert "MiB" in payload["timeline_omitted"]


def _count_passes(monkeypatch):
    """Every Plane 2 record pass and every Plane 1 conversion, by
    whoever makes it - the preflight included, not only the render."""
    from tools import bst_log_to_chrome_trace as plane1
    from tools import bst_native_build_tracer as tracer

    passes = {"plane2": 0, "plane1": 0, "preflight": 0}
    for module, name, key in ((tracer, "stream_records", "plane2"),
                              (plane1, "main", "plane1"),
                              (view, "predicted_tracks", "preflight")):
        real = getattr(module, name)

        def counting(*args, _real=real, _key=key, **kwargs):
            passes[_key] += 1
            return _real(*args, **kwargs)

        monkeypatch.setattr(module, name, counting)
    return passes


@pytest.mark.parametrize("ceiling", ["fits", "tracks", "bytes"])
def test_the_export_reads_each_plane_once(snapshot, tmp_path, monkeypatch,
                                          ceiling):
    """The review on `UX-1081`: the preflight re-did the render's whole
    preprocessing - Plane 1's conversion and the raw log's record pass,
    twice per step. One of each per export, whichever step fits."""
    if ceiling == "tracks":
        plane1 = render(str(snapshot), None, quiet=True, planes=PLANE1_ONLY,
                        tracks_only=True)
        monkeypatch.setattr(view, "TRACE_TRACK_BUDGET", plane1["tracks"])
    if ceiling == "bytes":
        monkeypatch.setattr(view, "TRACE_BUDGET_B", 1)
    passes = _count_passes(monkeypatch)

    view.export(str(snapshot / "run"), str(tmp_path / "report.html"))

    assert passes["preflight"] >= 1, passes
    assert passes == dict(passes, plane2=1, plane1=1), (
        f"{ceiling}: expected one record pass and one Plane 1 "
        f"conversion per export, preflight included: {passes}")


def test_counting_then_rendering_is_the_same_bytes(snapshot, tmp_path):
    """Counting first and then rendering from the shared inputs writes
    exactly the file a lone render does - a narrowed one included."""
    from tools.bga_timeline import shared_inputs

    def lone(name, **kwargs):
        render(str(snapshot), str(tmp_path / name), quiet=True, **kwargs)
        # Decompressed: the gzip header carries the file's name and mtime.
        return gzip.decompress((tmp_path / name).read_bytes())

    whole = lone("alone.json.gz")
    anchor = render(str(snapshot), None, quiet=True,
                    tracks_only=True)["anchor"]
    one = lone("alone-one.json.gz", only_element=anchor)
    assert one != whole
    with shared_inputs():
        counted = render(str(snapshot), None, quiet=True, tracks_only=True)
        drawn = render(str(snapshot), str(tmp_path / "shared.json.gz"),
                       quiet=True)
        render(str(snapshot), str(tmp_path / "shared-one.json.gz"),
               quiet=True, only_element=anchor)
    assert counted["tracks"] == drawn["tracks"]
    assert gzip.decompress((tmp_path / "shared.json.gz").read_bytes()) == whole
    assert gzip.decompress(
        (tmp_path / "shared-one.json.gz").read_bytes()) == one
