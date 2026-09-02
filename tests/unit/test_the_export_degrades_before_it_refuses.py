"""UX-530: a real capture met the track ceiling and lost the timeline whole.

`export()` refused, and printed beside the refusal a recipe naming the
flag that would have fitted - `--planes 1`, which `UX-430` measured at
16,832 tracks to 1,205 on the seeded scale run. The reader was told what
to run; the export never ran it.

**Two claims, two instruments.** The ladder is measured through a real
render of a real two-plane snapshot, with `TRACE_TRACK_BUDGET`
monkeypatched down so a fixture that renders in a moment sits over it -
the bound is not what is under test, the behaviour at the bound is.
`test_the_handoff_counts_what_perfetto_spends.py` holds the same
behaviour against a faked render, per step.

The second claim is the item's other half: the ceiling counts
**processes**, not slices. With the spine on, every dynamically-linked
process is recorded twice, and `merge_record_streams` (`UX-406`) is what
stops the *timeline* seeing two. `test_the_second_record_does_not_halve
_the_room` doubles a capture's records and measures that neither the
track count nor the slice count moves - the property the ceiling rests
on, held where a change to the join would break it.
"""
import gzip
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import bga_view as view                             # noqa: E402
from tools.bga_timeline import (                               # noqa: E402
    PLANE1_ONLY, PLANE_CHOICES, PLANES_BOTH, render)

node = __import__("shutil").which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: Small enough to render in a moment, large enough that elements, pids
#: and Plane 1's own tracks are three different numbers.
ELEMENTS, PER_ELEMENT = 4, 6


def _snapshot(into, doubled=False):
    """A two-plane snapshot. `doubled` records every process twice.

    Which is what a capture with the ptrace spine *is*: the spine sees
    every process and the hook sees every dynamically-linked one, so a
    dynamic process arrives on both streams (`UX-107`).
    """
    snapshot = pathlib.Path(into)
    snapshot.mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO / "tests/fixtures/golden/mixed_task_kinds",
                    snapshot / "run", dirs_exist_ok=True)
    (snapshot / "run" / "expected_output.json").unlink(missing_ok=True)
    with open(snapshot / "run" / "graph.json", encoding="utf-8") as handle:
        uids = [row["uid"] for row in json.load(handle)["elements"]][:ELEMENTS]

    def stamp(seconds):
        return (f"2026-08-21 12:{int(seconds) // 60:02d}:"
                f"{int(seconds) % 60:02d},"
                f"{int((seconds - int(seconds)) * 1000):03d}")

    lines = [f"[wrapper][{stamp(0)}] INFO: Executing command: bst build all.bst"]
    raw, pid = [], 100
    for index, uid in enumerate(uids):
        lines.append(f"[wrapper][{stamp(1.0 + index)}] INFO: [00:00:00]"
                     f"[{index:08x}][   build:{uid}] START Building")
        lines.append(f"[wrapper][{stamp(1.9 + index)}] INFO: [00:00:00]"
                     f"[{index:08x}][   build:{uid}] SUCCESS Building")
        for child in range(PER_ELEMENT):
            pid += 1
            began = 1000.0 + index + child / 100.0
            for src in (("spine", "hook") if doubled else ("spine",)):
                raw.append(f"START pid={pid} ppid=1 ts={began:.6f} "
                           f"element={uid} inv=inv-{index} src={src} "
                           f"cmd=cc -c f{child}.c\n")
                raw.append(f"END pid={pid} ppid=1 ts={began + 0.05:.6f} "
                           f"element={uid} inv=inv-{index} src={src} exit=0 "
                           f"utime=0.01 stime=0.01 maxrss_kb=1024 "
                           f"cmd=cc -c f{child}.c\n")
    lines.append(f"[wrapper][{stamp(9.0)}] INFO: Return code: 0")
    (snapshot / "build.log").write_text("\n".join(lines) + "\n",
                                        encoding="utf-8")
    with gzip.open(snapshot / "plane2.log.gz", "wt", encoding="utf-8") as out:
        out.write("".join(raw))
    return snapshot


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory):
    return _snapshot(tmp_path_factory.mktemp("degrade") / "20260821T120000Z")


class TestTheCeilingCountsProcesses:
    """The item's second clause. A track is opened per `(element, pid)`
    after the join, so the spine's second record is not a second row."""

    def test_the_second_record_does_not_halve_the_room(self, tmp_path):
        one = render(str(_snapshot(tmp_path / "one")),
                     str(tmp_path / "one.pftrace"), quiet=True)
        two = render(str(_snapshot(tmp_path / "two", doubled=True)),
                     str(tmp_path / "two.pftrace"), quiet=True)
        assert two["tracks"] == one["tracks"], (
            f"a capture recording every process twice drew "
            f"{two['tracks']} tracks against {one['tracks']} - the ceiling "
            f"is being spent on records rather than on processes")
        assert two["slices"] == one["slices"], (two["slices"], one["slices"])

    def test_the_track_count_is_the_process_population(self, snapshot,
                                                       tmp_path):
        """What the ceiling is actually counting, stated as an identity:
        one process lane per element, one thread lane per traced pid,
        and `UX-310`'s concurrency counter."""
        whole = render(str(snapshot), str(tmp_path / "both.pftrace"),
                       quiet=True)
        plane1 = render(str(snapshot), str(tmp_path / "one.pftrace"),
                        planes=PLANE1_ONLY, quiet=True)
        assert whole["tracks"] - plane1["tracks"] == (
            ELEMENTS + ELEMENTS * PER_ELEMENT + 1)


class TestTheLadder:

    def test_the_steps_are_the_renderers_own_choices(self):
        """Read off `PLANE_CHOICES` rather than restated here, so a
        third grain arriving in `bga_timeline` is a step this export
        tries rather than a flag its recipe names and it never runs."""
        steps = [step for step, _why in view._degradation_steps()]
        assert steps == list(PLANE_CHOICES), (
            f"the ladder is {steps} and the renderer offers "
            f"{list(PLANE_CHOICES)}")
        assert steps[0] == PLANES_BOTH, "the whole timeline is not tried first"

    def test_a_capture_over_the_ceiling_keeps_a_plane_1_timeline(
            self, snapshot, tmp_path, monkeypatch):
        """`UX-530`'s acceptance, through a real render. The budget is
        lowered rather than the fixture grown: `UX-430` measured where
        the bound belongs and this item's Out of Scope is that it stays
        there - what is under test is the behaviour at it."""
        whole = render(str(snapshot), str(tmp_path / "probe.pftrace"),
                       quiet=True)
        plane1 = render(str(snapshot), str(tmp_path / "probe1.pftrace"),
                        planes=PLANE1_ONLY, quiet=True)
        assert plane1["tracks"] < whole["tracks"], (plane1, whole)
        monkeypatch.setattr(view, "TRACE_TRACK_BUDGET", plane1["tracks"])

        path = tmp_path / "report.html"
        view.export(str(snapshot / "run"), str(path))
        text = path.read_text(encoding="utf-8")
        payload = json.loads(
            re.search(r'id="bga-run">(.*?)</script>', text, re.S).group(1))
        assert payload["has_timeline"] is True, payload.get("timeline_omitted")
        assert payload["trace_planes"] == ["1"]
        assert 'id="bga-trace"' in text, "the timeline was not inlined"
        said = payload["timeline_degraded"]
        assert "--planes 1" in said, said
        assert f"{whole['tracks']:,} tracks" in said, (
            f"the page does not say what the whole timeline would have "
            f"drawn: {said}")

    def test_a_capture_inside_the_ceiling_is_not_narrowed(self, snapshot,
                                                          tmp_path):
        path = tmp_path / "whole.html"
        view.export(str(snapshot / "run"), str(path))
        payload = json.loads(re.search(
            r'id="bga-run">(.*?)</script>',
            path.read_text(encoding="utf-8"), re.S).group(1))
        assert payload["trace_planes"] == ["1", "2"]
        assert "timeline_degraded" not in payload


_PROBE = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null };
const app = await import("./tests/viewer.mjs");

const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));
const find = (n, pred) => {
  if (!n) return null;
  if (pred(n)) return n;
  for (const c of n.children ?? []) { const hit = find(c, pred); if (hit) return hit; }
  return null;
};
const intro = (options) => find(
  app.renderQuestions(_makeNode, options), (n) => n.tagName === "p");

const NARROWED = { hasTimeline: true, tracePlanes: ["1"], elements: [],
                   timelineDegraded: "The whole timeline did not fit - it "
                     + "draws 8,159 tracks - so this file carries "
                     + "`--planes 1`: 842 tracks." };
console.log = (...a) => process.stdout.write(a.join(" ") + "\\n");
console.log(JSON.stringify({
  narrowed: text(intro(NARROWED)),
  narrowedFlag: intro(NARROWED).attrs["data-degraded"],
  plane1: text(intro({ ...NARROWED, timelineDegraded: undefined })),
  plane1Flag: intro({ ...NARROWED, timelineDegraded: undefined })
    .attrs["data-degraded"],
}));
"""


@pytest.fixture(scope="module")
def probed():
    result = subprocess.run(
        [node, "--input-type=module", "-e", _PROBE],
        capture_output=True, text=True, cwd=REPO, timeout=60,
        env=dict(os.environ, BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs")))
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout)


@needs_node
class TestTheHandoffSentenceStatesTheStep:

    def test_a_narrowed_page_says_which_step_and_what_it_cost(self, probed):
        said = probed["narrowed"]
        assert "8,159 tracks" in said and "--planes 1" in said, said
        assert "Plane 2 is not in it" in said, (
            "the narrowed page dropped the sentence that says which "
            f"queries answer: {said}")
        assert probed["narrowedFlag"] == "true"

    def test_a_plane_1_capture_is_not_told_it_was_narrowed(self, probed):
        """The other direction, and the one that discriminates: a run
        that only ever had one plane must not be told this file dropped
        the other."""
        said = probed["plane1"]
        assert "--planes 1" not in said, said
        assert "did not fit" not in said, said
        # An unset attribute is `undefined`, which `JSON.stringify`
        # drops - so the key's absence *is* the assertion.
        assert probed.get("plane1Flag") is None, probed


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
