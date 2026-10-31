"""UX-1359: a chain element worth a share of the build and busy on under half its granted width gets a line.

fdsdk's openssl.bst held 5.6% of the chain at 1.49 of 4 cores and whatif saves 600.7 s; correlate said nothing.
The line names both readings, in correlate, in analyze's finding (where `--explain` prints its rule) and on the page:
styleguide §1b, the finding reaches the decision panel and the element card.
"""

import json
import sys

import pytest

from bga.analyzer import BuildEfficiencyAnalyzer
from bga.correlate import correlate, format_correlation
from bga.findings import compute_findings
from tests.browser import NO_BROWSER, Browser, find_chrome
from tests.fixtures.topologies import _build, _dependency, _element, _span, write_run_dir

S = 1_000_000
# `slow.bst` is openssl: a tenth of a 100 s chain, 1.49 of its 4 cores busy.
CHAIN = {"base.bst": 40 * S, "slow.bst": 10 * S, "top.bst": 50 * S}
CORES = {"base.bst": 3.6, "slow.bst": 1.49, "top.bst": 3.5}
LINE = "but kept 1.49 of its 4 granted cores busy (37.2%)"


def _native(cores=CORES):
    return {
        "by_element": dict.fromkeys(cores, 1),
        "per_element_parallelism": [
            {"element": uid, "requested_jobs": 1, "resolved_jobs": 4, "findings": []} for uid in cores
        ],
        "cpu_time": {"per_element": {uid: {"cpu_per_wall_second": c, "coverage": 1.0} for uid, c in cores.items()}},
    }


def _topology():
    uids = list(CHAIN)
    elements = [
        dict(_element(uid, requested_target=uid == uids[-1]), element_kind="autotools", max_jobs=4) for uid in uids
    ]
    dependencies = [_dependency(uids[i - 1], uids[i]) for i in range(1, len(uids))]
    spans, at = [], 0
    for uid in uids:
        spans.append(_span(uid, at, CHAIN[uid]))
        at += CHAIN[uid]
    return _build(elements, dependencies, spans, wall_end_us=at, max_jobs=4)


@pytest.fixture(scope="module")
def analysed(tmp_path_factory):
    snapshot = tmp_path_factory.mktemp("width")
    run_dir = write_run_dir(snapshot, _topology(), name="run")
    (snapshot / "plane2.json").write_text(json.dumps(_native()))
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()
    result.plane2_report = _native()
    from bga.report.json import format_json

    return run_dir, result, json.loads(format_json(result))


def _slow(joined):
    return next(e for e in joined["elements"] if e["element"] == "slow.bst")


def test_correlate_gives_the_chain_element_one_line_naming_both_readings(analysed):
    _run, _result, analysis = analysed
    joined = correlate(analysis, _native())
    texts = [r["text"] for r in _slow(joined)["recommendations"] if r["id"] == "below-granted-width"]
    assert len(texts) == 1
    assert "fixing it is worth 10.0 s (10.0% of the build)" in texts[0] and LINE in texts[0]
    assert "slow.bst" in [e["element"] for e in joined["actionable"]]
    assert LINE in format_correlation(joined).split("What to do next")[1]


def test_an_element_busy_on_half_its_width_or_worth_too_little_is_not_told(analysed):
    _run, _result, analysis = analysed
    busy = correlate(analysis, _native({**CORES, "slow.bst": 2.0}))
    assert not [r for r in _slow(busy)["recommendations"] if r["id"] == "below-granted-width"]
    cheap = json.loads(json.dumps(analysis))
    for d in cheap["critical_path_detail"]:
        if d["element_uid"] == "slow.bst":
            d["realizable_saving_us"] = int(0.004 * cheap["total_duration_us"])
    assert not [r for r in _slow(correlate(cheap, _native()))["recommendations"] if r["id"] == "below-granted-width"]


def test_a_compute_bound_verdict_does_not_stand_under_half_the_width(analysed):
    """1.49 clears correlate's 1.25 compute-bound line; under half of 4 it must not read 'already compute-bound'."""
    _run, _result, analysis = analysed
    ids = [r["id"] for r in _slow(correlate(analysis, _native()))["recommendations"]]
    assert "already-compute-bound" not in ids


def test_analyze_publishes_the_same_line_as_a_finding_with_its_rule(analysed):
    _run, result, analysis = analysed
    finding = next(f for f in compute_findings(result) if f["id"] == "below-granted-width")
    assert finding["title"] == "10.0 s on slow.bst at 1.49 of 4 granted cores busy"
    correlate_text = next(
        r["text"] for r in _slow(correlate(analysis, _native()))["recommendations"] if r["id"] == "below-granted-width"
    )
    assert finding["detail"] == [f"    slow.bst: {correlate_text}"]
    rule = next(p for p in analysis["provenance"] if p["claim"] == "below-granted-width")["rule"]
    assert rule["name"] == "_WIDTH_UNUSED_SHARE" and rule["threshold"] == 0.5


_READ = r"""
(async () => {
  for (let i = 0; i < 100 && !document.querySelector('[data-section="decision"]'); i++) {
    await new Promise((r) => setTimeout(r, 100));
  }
  const panel = document.querySelector('[data-section="decision"] li.next-step[data-step="build-it-wider"]');
  const card = () => document.getElementById("element-slow-bst");
  for (let i = 0; i < 100 && !(card()?.textContent ?? "").includes("granted"); i++) {
    await new Promise((r) => setTimeout(r, 100));
  }
  return {panel: panel ? panel.textContent : null, card: card()?.textContent ?? null};
})()
"""


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
def test_the_decision_panel_and_the_element_card_carry_the_line(analysed, tmp_path):
    sys.path.insert(0, ".")
    from tools.bga_view import export

    run_dir, _result, _analysis = analysed
    page = tmp_path / "page.html"
    export(str(run_dir), str(page), with_trace=False, reanalyse=True)
    with Browser(find_chrome()) as browser:
        read = browser.measure(page.as_uri() + "#element-slow-bst", _READ)
    assert read["panel"] and "slow.bst: holds 10.0% of the critical path" in read["panel"] and LINE in read["panel"]
    assert "bga correlate" in read["panel"]
    assert read["card"] and LINE in read["card"]
