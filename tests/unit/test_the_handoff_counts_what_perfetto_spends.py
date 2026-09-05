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

from tests import pages
from tools import bga_view as view
from tools.bga_timeline import PLANE1_ONLY, describe, render

#: Small enough to render in a moment, large enough that elements and
#: pids are different numbers - a fixture where they agree cannot tell
#: a per-element track from a per-pid one.
PER_ELEMENT = 3


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory):
    return pages.scale_two_plane_snapshot(
        tmp_path_factory.mktemp("tracks"), per_element=PER_ELEMENT)


def _population(snapshot, per_element=None):
    """`(elements, pids)` from the fixture's own two logs.

    `per_element` defaults to this file's own fixture density; `UX-445`
    passes another so the same identity can be asked at a second point.
    """
    with open(pathlib.Path(snapshot) / "run" / "graph.json",
              encoding="utf-8") as handle:
        elements = len(json.load(handle)["elements"])
    return elements, elements * (PER_ELEMENT if per_element is None
                                 else per_element)


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


class TestTheCostModelIsLinearAndNotFittedAtOnePoint:
    """`UX-445`, the half of it this repository can measure.

    The clause above asserts the identity at **one** population, which
    is enough to catch a second track per pid and not enough to say the
    relationship is linear - and `TRACE_TRACK_BUDGET` is a threshold on
    a line. Measured on the seeded scale run at four process densities:

    ```text
      per element   tracks   slices     bytes   render s   --planes 1
                1    3,610    2,406   138,489        0.3        1,205
                4    7,216    6,012   240,398        0.6        1,205
               12   16,832   15,628   491,397        1.4        1,205
               24   31,256   30,052   865,529        2.5        1,205
    ```

    `tracks = 2,407 + 1,202 x per_element` across all four, and Plane
    1's own track count does not move at all - so `--planes 1` is a
    3.0x reduction at one process an element and a **25.9x** reduction
    at twenty-four. The narrowing control gets better exactly where the
    reader needs it, which is a fact `UX-430` could not state from its
    single point.

    Two densities are exercised here rather than four: the identity is
    what is being checked, and a third and fourth point cost a fixture
    each without changing what a red would mean.
    """

    @pytest.mark.parametrize("per_element", [1, 8])
    def test_the_identity_holds_at_another_density(
            self, tmp_path_factory, tmp_path, per_element):
        other = pages.scale_two_plane_snapshot(
            tmp_path_factory.mktemp(f"tracks{per_element}"),
            per_element=per_element)
        whole = render(str(other), str(tmp_path / "both.pftrace"))
        plane1 = render(str(other), str(tmp_path / "p1.pftrace"),
                        planes=PLANE1_ONLY)
        elements, pids = _population(other, per_element)
        assert whole["tracks"] - plane1["tracks"] == elements + pids + 1, (
            f"at {per_element} processes an element the emitter added "
            f"{whole['tracks'] - plane1['tracks']} tracks for {elements} "
            f"elements and {pids} pids - the cost model is not the line "
            f"`TRACE_TRACK_BUDGET` is a threshold on")
        assert plane1["tracks"] == 1_205, (
            f"Plane 1 opened {plane1['tracks']} tracks at "
            f"{per_element} processes an element; it does not depend on "
            f"the process population, which is what makes `--planes 1` a "
            f"reduction that grows with the density")


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
    something that is not the cost.

    `UX-530` moved what a refusal *is*: the export renders again at each
    grain `_degradation_steps` names before it refuses anything, so the
    fake below answers per step - `whole` for the two-plane render and
    `narrowed` for `--planes 1`, which is how `UX-430`'s own curve
    behaves (16,832 tracks and 486,167 B become 1,205 and 72,080).
    """

    GOLDEN = str(REPO / "tests/fixtures/golden/mixed_task_kinds")

    def _export(self, monkeypatch, tmp_path, whole, narrowed=None):
        """`whole`/`narrowed` are `(bytes, tracks)` for the two steps."""
        narrowed = whole if narrowed is None else narrowed

        def fake(_run, planes=None):
            size, tracks = narrowed if planes == PLANE1_ONLY else whole
            return (b"\x1f\x8b" + b"x" * size,
                    ["1"] if planes == PLANE1_ONLY else ["1", "2"],
                    None, tracks)

        monkeypatch.setattr(view, "trace_with_planes", fake)
        path = tmp_path / "report.html"
        view.export(self.GOLDEN, str(path))
        return json.loads(_payload(path, "bga-run"))

    def test_too_many_tracks_degrades_instead_of_refusing(self, monkeypatch,
                                                          tmp_path):
        """`UX-530`'s acceptance. The capture that met the ceiling lost
        the timeline whole, and the flag that would have fitted was
        named in the recipe printed beside the refusal."""
        payload = self._export(
            monkeypatch, tmp_path, (4096, view.TRACE_TRACK_BUDGET + 1),
            narrowed=(1024, 1_205))
        assert payload["has_timeline"] is True, payload.get(
            "timeline_omitted")
        said = payload["timeline_degraded"]
        assert "--planes 1" in said and "1,205 tracks" in said, said
        assert f"{view.TRACE_TRACK_BUDGET + 1:,} tracks" in said, (
            "the page does not say what the whole timeline would have "
            f"drawn, so the narrowing reads as a preference: {said}")
        assert payload["trace_planes"] == ["1"]

    def test_a_narrowing_that_still_does_not_fit_names_both(self,
                                                            monkeypatch,
                                                            tmp_path):
        """Refusal is what is left, and it accounts for every step."""
        over = (4096, view.TRACE_TRACK_BUDGET + 1)
        payload = self._export(monkeypatch, tmp_path, over, narrowed=over)
        said = payload["timeline_omitted"]
        assert payload["has_timeline"] is False
        assert "the whole timeline" in said and "--planes 1" in said, said
        assert said.count("tracks, over") == 2, said

    def test_too_many_bytes_is_still_refused_in_bytes(self, monkeypatch,
                                                      tmp_path):
        payload = self._export(monkeypatch, tmp_path,
                               (view.TRACE_BUDGET_B * 2, 1))
        said = payload["timeline_omitted"]
        assert "MiB" in said and "track" not in said, said

    def test_a_trace_inside_both_bounds_is_carried_undegraded(self,
                                                              monkeypatch,
                                                              tmp_path):
        payload = self._export(monkeypatch, tmp_path,
                               (4096, view.TRACE_TRACK_BUDGET))
        assert payload["has_timeline"] is True, payload.get(
            "timeline_omitted")
        assert "timeline_degraded" not in payload, (
            "a timeline that fitted whole says it was narrowed")

    def test_the_refusal_names_the_flags_that_make_it_smaller(
            self, monkeypatch, tmp_path):
        over = (4096, view.TRACE_TRACK_BUDGET + 1)
        payload = self._export(monkeypatch, tmp_path, over, narrowed=over)
        note = payload["timeline_recipe"]["note"]
        assert "--planes 1" in note and "--only-element" in note, note


def _payload(path, ident):
    import re

    text = pathlib.Path(path).read_text(encoding="utf-8")
    return re.search(rf'id="{ident}">(.*?)</script>', text, re.S).group(1)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
