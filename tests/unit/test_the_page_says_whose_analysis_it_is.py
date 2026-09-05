"""UX-533: the served page is the capture-time analysis, and said so nowhere.

`bga view` served `published_analysis(run) or _analyze_now(run)` and the
two rendered identically. Measured here on `tests/fixtures/with_timeline`,
which carries an `analyze.json` written before the producer stamp:

```text
$ python -c "... payloads(run) vs payloads(run, reanalyse=True)"
stored keys 41 · fresh keys 43 · added by this build: producer, run_instance
```

Two keys on a fixture that is nearly current; the field case in the item
is six page sections and nine coverage terms. Either way the page had
nothing to say which document it had.

**The discriminating clause is the producer comparison.** `stale` is
`UX-249`'s contract set and nothing else - not a key count, which would
call a run stale for having nothing to put in a section, and not a
version string, which Direction 10 argues is a lossy summary of nine
contracts. `test_a_stored_analysis_from_this_build_is_not_stale` is the
other direction: the same code path, a stamp that agrees, no sentence.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import producer
from tools import bga_view as view

RUN = REPO / "tests/fixtures/with_timeline/run"
STORED = REPO / "tests/fixtures/with_timeline/analyze.json"

node = __import__("shutil").which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _stamped(contracts):
    """A stored analysis whose producer records `contracts`."""
    document = json.loads(STORED.read_text(encoding="utf-8"))
    document["producer"] = {"tool": "bga", "version": "0.2.9",
                            "contracts": list(contracts)}
    return document


class TestWhichAnalysisThisIs:

    def test_an_unstamped_capture_is_stale_and_says_it_cannot_count(self):
        """Every artifact written before `UX-249`. The absence is a
        state with consequences, not agreement with this build."""
        note = view.analysis_source(json.loads(
            STORED.read_text(encoding="utf-8")), reanalysed=False)
        assert note["source"] == view.ANALYSIS_FROM_CAPTURE
        assert note["stored_producer"] == producer.UNSTAMPED
        assert note["stale"] is True
        assert note["contracts_moved"] == [], (
            "an unstamped capture cannot name a contract that moved")

    def test_a_stored_analysis_from_this_build_is_not_stale(self):
        """The clause that makes the sentence discriminate. Same run,
        same code path, a stamp that agrees - and no claim of staleness,
        so a page that says it every time fails here."""
        note = view.analysis_source(
            _stamped(producer.stamp()["contracts"]), reanalysed=False)
        assert note["stale"] is False, note["contracts_moved"]

    def test_a_moved_contract_is_named_in_the_direction_it_moved(self):
        """Derived, not spelled. The first draft named `analyze/v4`,
        and `UX-535` bumped to v5 in the same round: the clause went
        green because the id it dropped was no longer in the stamp at
        all, which is the shape it exists to catch."""
        from bga import schemas

        mine = producer.stamp()["contracts"]
        current = schemas.ANALYZE
        assert current in mine, (current, mine)
        previous = f"{current.rsplit('/v', 1)[0]}/v{int(current.rsplit('/v', 1)[1]) - 1}"
        theirs = [name for name in mine if name != current]
        note = view.analysis_source(_stamped(theirs), reanalysed=False)
        assert note["stale"] is True
        assert f"{previous} → {current}" in note["contracts_moved"], note

    def test_the_count_is_of_sections_this_build_always_publishes(self):
        """`ANALYZE_FULL_KEYS`, not the schema's 56 properties: a
        conditional section a run has nothing to put in is not something
        re-analysing would add, and counting it would overstate."""
        from bga import schemas

        note = view.analysis_source({"schema": "analyze/v4"}, reanalysed=False)
        assert note["sections_declared"] == len(schemas.ANALYZE_FULL_KEYS)
        assert len(note["sections_absent"]) == len(schemas.ANALYZE_FULL_KEYS) - 1

    def test_analysing_here_is_a_different_source(self):
        note = view.analysis_source(None, reanalysed=True)
        assert note["source"] == view.ANALYSIS_FROM_VIEW
        assert note["stale"] is False


class TestTheFlagChangesWhatIsServed:

    def test_reanalyse_returns_this_builds_answer(self):
        stored = view.payloads(str(RUN))["report.json"]
        fresh = view.payloads(str(RUN), reanalyse=True)["report.json"]
        added = set(fresh) - set(stored)
        assert added, (
            "re-analysing added no key the stored document lacked, so the "
            "flag cannot be shown to do anything on this fixture")
        assert "producer" in added

    def test_view_never_writes_the_stored_analysis(self, tmp_path):
        """The Out of Scope, as a guard: the capture-time analysis is
        what the CI comment quotes, and `bga view` reads it."""
        snapshot = tmp_path / "snap"
        shutil.copytree(REPO / "tests/fixtures/with_timeline", snapshot)
        stored = snapshot / "analyze.json"
        before = (stored.read_bytes(), os.stat(stored).st_mtime_ns)
        for flag in (False, True):
            view.export(str(snapshot / "run"), str(tmp_path / "out.html"),
                        with_trace=False, reanalyse=flag)
        assert (stored.read_bytes(), os.stat(stored).st_mtime_ns) == before

    def test_the_flag_reaches_the_command_line(self):
        result = subprocess.run(
            [sys.executable, "-m", "bga.cli", "view", "--help"],
            capture_output=True, text=True, cwd=REPO, timeout=120)
        assert "--reanalyse" in result.stdout, result.stdout[-2000:]

    def test_the_export_carries_the_note_the_page_reads(self, tmp_path):
        path = tmp_path / "report.html"
        view.export(str(RUN), str(path), with_trace=False)
        run = json.loads(_payload(path, "bga-run"))
        assert run["analysis"]["source"] == view.ANALYSIS_FROM_CAPTURE
        assert run["analysis"]["stale"] is True


_PROBE = """
// `UX-537`: the shared shim with one override, not a hand-built
// document. The override is the whole of what this harness needs
// that the shim's defaults do not give it: one slot to draw into.
const shim = await import(process.env.BGA_DOM_SHIM);
const slot = shim.makeNode("p");
slot.hidden = true;
shim.installDocument({
  getElementById: (id) => (id === "run-producer" ? slot : null),
});
const app = await import("./tests/viewer.mjs");

const STALE = { source: "capture", stored_producer: "0.2.9",
                this_build: "0.3.0", contracts_moved: ["analyze/v3 -> v4"],
                sections_declared: 35, sections_absent: ["a", "b", "c"],
                stale: true, reanalyse: "bga view RUN --reanalyse" };
const CURRENT = { ...STALE, contracts_moved: [], sections_absent: [],
                  stale: false };
const HERE = { ...STALE, source: "view", stale: false };

app.stampHeader(document, { producer: { tool: "bga", version: "0.3.0" } },
                { analysis: STALE });
console.log = (...a) => process.stdout.write(a.join(" ") + "\\n");
console.log(JSON.stringify({
  stale: app.analysisSentence(STALE),
  current: app.analysisSentence(CURRENT),
  here: app.analysisSentence(HERE),
  absent: app.analysisSentence(undefined),
  header: slot._text ?? "",
  source: slot.attrs["data-analysis-source"],
  flagged: slot.attrs["data-analysis-stale"],
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
class TestThePageStatesIt:

    def test_a_stale_capture_names_the_count_and_the_flag(self, probed):
        said = probed["stale"]
        assert "analysed at capture" in said and "0.2.9" in said, said
        assert "3 of the 35 sections" in said, said
        assert "--reanalyse" in said, said

    def test_a_current_capture_makes_no_claim_about_staleness(self, probed):
        """The mutation the item names, from the other side: a sentence
        printed unconditionally passes the clause above and fails here."""
        assert probed["current"] == "analysed at capture by bga 0.2.9"

    def test_an_analysis_computed_here_says_so(self, probed):
        assert probed["here"] == "analysed here by bga 0.3.0"

    def test_a_run_with_no_note_says_nothing(self, probed):
        assert probed["absent"] is None

    def test_the_heading_carries_it_beside_the_producer_stamp(self, probed):
        assert "measured by bga 0.3.0" in probed["header"], probed["header"]
        assert "analysed at capture" in probed["header"], probed["header"]
        assert probed["source"] == "capture"
        assert probed["flagged"] == "true"


def _payload(path, ident):
    import re

    text = pathlib.Path(path).read_text(encoding="utf-8")
    return re.search(rf'id="{ident}">(.*?)</script>', text, re.S).group(1)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
