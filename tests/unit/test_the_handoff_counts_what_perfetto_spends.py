"""UX-430: the handoff's bound was in bytes, and Perfetto spends tracks.

`TRACE_BUDGET_B` gates two things - whether the export inlines the trace
and whether the served page copies it or deep-links it - and it bounds
both correctly. It simply measures a different quantity from the one
that decides whether the file opens: Perfetto draws a **row per track**,
and `_write_trackevent` opens one process track per element and one
thread track per traced pid, so the track count rises with the process
population.

Measured here on the seeded scale run (1,202 elements, twelve processes
an element):

```text
                  tracks   slices     bytes   share of TRACE_BUDGET_B
  both planes     16,832   15,628   486,167   11.6%
  --planes 1       1,205    1,204    72,080    1.7%
  --only-element   1,219    1,216    73,017    1.7%
```

More tracks than slices, at an eighth of the byte bound. That is the
fixing guide's §5 on the design side: a real number, cheaply obtained
and honestly reported, measuring the wrong thing.

The clause that decides is
`test_the_track_count_is_the_population_and_not_the_bytes`, which
asserts the **identity** between the population and the track count - so
a change that opens a second track per pid reddens it while the byte
figure moves by a rounding error, which is the mutation the item names.
"""
import json
import os
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages                                        # noqa: E402
from tools.bga_timeline import (                               # noqa: E402
    PLANE1_ONLY, describe, render)
from tools import bga_view as view                             # noqa: E402

#: Small enough to render in a moment, large enough that elements and
#: pids are different numbers - a fixture where they agree cannot tell
#: a per-element track from a per-pid one.
PER_ELEMENT = 3


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory):
    return pages.scale_two_plane_snapshot(
        tmp_path_factory.mktemp("tracks"), per_element=PER_ELEMENT)


def _population(snapshot):
    """`(elements, pids)` from the fixture's own two logs."""
    with open(pathlib.Path(snapshot) / "run" / "graph.json",
              encoding="utf-8") as handle:
        elements = len(json.load(handle)["elements"])
    return elements, elements * PER_ELEMENT


class TestTheBoundIsInTheUnitTheViewerSpends:

    def test_the_track_count_is_the_population_and_not_the_bytes(
            self, snapshot, tmp_path):
        """What Plane 2 **adds**: one process track per element, one
        thread track per traced pid, and the concurrency counter's own
        track. Written as an increment over the Plane-1-only render
        rather than as a total, so it says what the process population
        costs without also pinning what Plane 1 happens to open - and so
        a second track per pid reddens it while the byte figure moves by
        a rounding error, which is the mutation this item names."""
        whole = render(str(snapshot), str(tmp_path / "both.pftrace"))
        plane1 = render(str(snapshot), str(tmp_path / "p1.pftrace"),
                        planes=PLANE1_ONLY)
        elements, pids = _population(snapshot)
        assert whole["tracks"] - plane1["tracks"] == elements + pids + 1, (
            f"Plane 2 added {whole['tracks'] - plane1['tracks']} tracks for "
            f"{elements} elements and {pids} traced pids - the emitter is "
            f"opening a different number per process than the bound in "
            f"`TRACE_TRACK_BUDGET` was measured against")

    def test_the_bytes_do_not_see_it(self, snapshot, tmp_path):
        """The defect, stated as a comparison. The trace is a fraction
        of the byte bound and carries more tracks than slices."""
        result = render(str(snapshot), str(tmp_path / "both.pftrace"))
        size = os.path.getsize(tmp_path / "both.pftrace")
        assert result["tracks"] > result["slices"], (
            result["tracks"], result["slices"])
        assert size < view.TRACE_BUDGET_B / 4, (
            f"{size} B is no longer a small share of the "
            f"{view.TRACE_BUDGET_B} B bound, so this fixture no longer "
            f"shows the two quantities disagreeing")


class TestTheReaderCanAskForLess:

    def test_plane_one_only_drops_the_process_lanes(self, snapshot,
                                                    tmp_path):
        elements, _pids = _population(snapshot)
        narrowed = render(str(snapshot), str(tmp_path / "one.pftrace"),
                          planes=PLANE1_ONLY)
        whole = render(str(snapshot), str(tmp_path / "both.pftrace"))
        assert narrowed["tracks"] < whole["tracks"] / 2, (
            narrowed["tracks"], whole["tracks"])
        assert narrowed["planes"] == ["1"], narrowed["planes"]
        assert narrowed["tracks"] == elements + 3, narrowed["tracks"]

    def test_it_says_the_raw_log_is_still_there(self, snapshot, tmp_path):
        """Narrowing is not the same as a capture that never had a
        second plane, and the sentence has to tell them apart."""
        narrowed = render(str(snapshot), str(tmp_path / "one.pftrace"),
                          planes=PLANE1_ONLY)
        assert "--planes 1" in narrowed["omitted"], narrowed["omitted"]
        assert "still beside the snapshot" in narrowed["omitted"]

    def test_one_element_narrows_lanes_flows_and_counter_together(
            self, snapshot, tmp_path):
        """All three fold from the same record list, so a filter applied
        anywhere else would leave one element's lanes under the whole
        build's counter."""
        with open(pathlib.Path(snapshot) / "run" / "graph.json",
                  encoding="utf-8") as handle:
            uid = json.load(handle)["elements"][1]["uid"]
        one = render(str(snapshot), str(tmp_path / "one-el.pftrace"),
                     only_element=uid)
        whole = render(str(snapshot), str(tmp_path / "both.pftrace"))
        plane1 = render(str(snapshot), str(tmp_path / "p1.pftrace"),
                        planes=PLANE1_ONLY)
        assert one["only_element"] == uid
        # One element's process lane, its pids' thread lanes, and the
        # counter - the same increment as above with the population
        # reduced to one element.
        assert one["tracks"] - plane1["tracks"] == PER_ELEMENT + 2, (
            one["tracks"], plane1["tracks"])
        assert one["counters"] < whole["counters"], (
            "the concurrency counter still reads the whole build, so the "
            "lanes and the counter disagree about what is being shown")

    def test_the_narrowing_is_offered_where_the_size_is_reported(
            self, snapshot, tmp_path):
        """A flag a reader finds in `--help` after the file will not
        open is a flag that arrived too late."""
        result = render(str(snapshot), str(tmp_path / "both.pftrace"))
        said = describe(result, str(tmp_path / "both.pftrace"))
        assert "tracks" in said, said
        assert "--planes 1" in said and "--only-element" in said, said

    def test_a_narrowed_run_says_what_it_narrowed_to(self, snapshot,
                                                     tmp_path):
        with open(pathlib.Path(snapshot) / "run" / "graph.json",
                  encoding="utf-8") as handle:
            uid = json.load(handle)["elements"][1]["uid"]
        one = render(str(snapshot), str(tmp_path / "one-el.pftrace"),
                     only_element=uid)
        said = describe(one, str(tmp_path / "one-el.pftrace"))
        assert uid in said, said
        assert "--planes 1" not in said, (
            "a run that is already narrowed is told to narrow it again")


class TestARefusalNamesTheBoundItHit:
    """`UX-430`'s third clause. The two bounds measure different things,
    so a refusal that names the wrong one sends the reader to compress
    something that is not the cost."""

    GOLDEN = str(REPO / "tests/fixtures/golden/mixed_task_kinds")

    def _export(self, monkeypatch, tmp_path, size, tracks):
        monkeypatch.setattr(
            view, "trace_with_planes",
            lambda _run: (b"\x1f\x8b" + b"x" * size, ["1", "2"], None,
                          tracks))
        path = tmp_path / "report.html"
        view.export(self.GOLDEN, str(path))
        payload = json.loads(_payload(path, "bga-run"))
        return payload

    def test_too_many_tracks_is_refused_in_tracks(self, monkeypatch,
                                                  tmp_path):
        payload = self._export(monkeypatch, tmp_path, 4096,
                               view.TRACE_TRACK_BUDGET + 1)
        said = payload["timeline_omitted"]
        assert "tracks" in said and "MiB ceiling" not in said, said
        assert payload["has_timeline"] is False

    def test_too_many_bytes_is_still_refused_in_bytes(self, monkeypatch,
                                                      tmp_path):
        payload = self._export(monkeypatch, tmp_path,
                               view.TRACE_BUDGET_B * 2, 1)
        said = payload["timeline_omitted"]
        assert "MiB" in said and "track" not in said, said

    def test_a_trace_inside_both_bounds_is_carried(self, monkeypatch,
                                                  tmp_path):
        payload = self._export(monkeypatch, tmp_path, 4096,
                               view.TRACE_TRACK_BUDGET)
        assert payload["has_timeline"] is True, payload.get(
            "timeline_omitted")

    def test_the_refusal_names_the_flags_that_make_it_smaller(
            self, monkeypatch, tmp_path):
        payload = self._export(monkeypatch, tmp_path, 4096,
                               view.TRACE_TRACK_BUDGET + 1)
        note = payload["timeline_recipe"]["note"]
        assert "--planes 1" in note and "--only-element" in note, note


def _payload(path, ident):
    import re

    text = pathlib.Path(path).read_text(encoding="utf-8")
    return re.search(rf'id="{ident}">(.*?)</script>', text, re.S).group(1)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
