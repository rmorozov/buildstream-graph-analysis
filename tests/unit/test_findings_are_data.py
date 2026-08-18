"""UX-75: the report's conclusions, as data.

Measured on round 9's real capture, neither format was a superset of the
other: `--format json` published every *number* and none of the
conclusions, while the text report published the conclusions and only
part of the data. A CI gate - the consumer this project exists to serve -
had to re-implement `heaviest_on_path`'s structural exclusion and
re-derive four thresholds out of `bga/report/text.py` to reach what a
human read for free, and two implementations of one judgement is how
`bga analyze` and `bga correlate` had already drifted (`UX-71`).
"""
import json

from bga.findings import compute_findings, findings_by_id, render_findings
from bga.ingest.models import AnalysisResult
from bga.report.json import format_json
from bga.report.text import format_text


def _element(uid, dur_us, share, saving=None, structural=False):
    return {
        "element_uid": uid, "duration_us": dur_us, "share_of_path": share,
        "is_structural_kind": structural,
        "element_kind": "import" if structural else "manual",
        "realizable_saving_us": saving,
    }


def _real_shaped_result():
    """Round 9's shape: execution-bound, chain-bound, concentrated."""
    return AnalysisResult(
        attribution={"execution_on_chain_us": 3_583_900_000,
                     "untracked_head_us": 3_470_000},
        floors={"t_infinity_observed": 3_583_900_000, "efficiency_score": 1.0},
        total_duration_us=3_587_600_000,
        confidence={"primary": 1.0, "run_mode": "incremental"},
        signals={
            "critical_path": ["a.bst", "b.bst"],
            "critical_path_detail": [
                _element("components/_private/cmake-stage1.bst", 1_569_800_000,
                         0.435, 1_569_800_000),
                _element("components/openssl.bst", 672_100_000, 0.186, 522_550_000),
            ],
            "zero_slack_share": 0.77,
            "joint_saving": {
                "elements": ["components/_private/cmake-stage1.bst",
                             "components/openssl.bst"],
                "joint_saving_us": 2_092_300_000,
                "sum_of_individual_us": 2_092_300_000,
                "savings_add": True,
            },
            "optimization_horizon": [
                {"element_uid": "components/_private/cmake-stage1.bst",
                 "saving_us": 1_569_800_000, "makespan_after_us": 2_040_750_000,
                 "cumulative_saving_us": 1_569_750_000, "entering": []},
                {"element_uid": "components/openssl.bst", "saving_us": 522_550_000,
                 "makespan_after_us": 1_518_200_000,
                 "cumulative_saving_us": 2_092_300_000, "entering": []},
            ],
            "latent_heavies": [
                {"element_uid": "components/_private/git-minimal.bst",
                 "duration_us": 547_700_000},
            ],
        },
    )


# --- the conclusions reach the JSON ------------------------------------


def test_the_json_report_carries_the_findings():
    data = json.loads(format_json(_real_shaped_result()))

    assert "findings" in data
    ids = [f["id"] for f in data["findings"]]
    assert "execution-bound" in ids
    assert "time-concentration" in ids
    assert "joint-saving" in ids


def test_a_consumer_can_decide_chain_bound_without_reading_the_renderer():
    """The specific thing a CI gate had to re-derive: `_CHAIN_BOUND_RATIO`
    lived in `bga/report/text.py` and nothing published its verdict."""
    data = json.loads(format_json(_real_shaped_result()))
    by_id = {f["id"]: f for f in data["findings"]}

    assert by_id["time-concentration"]["evidence"]["chain_bound"] is True


def test_every_finding_carries_an_id_a_severity_and_its_numbers():
    """Ids are the contract - a gate keys on them and a run-to-run diff
    joins on them - so a wording change must not move a consumer."""
    for finding in compute_findings(_real_shaped_result()):
        assert finding["id"]
        assert finding["severity"] in {"critical", "high", "medium", "info"}
        assert isinstance(finding["title"], str) and finding["title"]
        assert isinstance(finding["evidence"], dict)


def test_ids_are_unique_within_one_report():
    findings = compute_findings(_real_shaped_result())

    assert len(findings_by_id(findings)) == len(findings)


# --- and the text renders *from* them ----------------------------------


def test_the_text_report_renders_the_findings_and_nothing_else():
    result = _real_shaped_result()
    key_findings = format_text(result).split("Confidence:\n")[0]

    for line in render_findings(compute_findings(result)):
        assert line in key_findings


def test_a_finding_that_is_not_produced_appears_in_neither_format():
    """The property `UX-75` is for: one place decides what is worth
    saying. A run with no joint saving computed loses that sentence from
    the text report *and* from the JSON, without either renderer knowing
    about the other."""
    result = _real_shaped_result()
    result.signals["joint_saving"] = None

    text = format_text(result)
    data = json.loads(format_json(result))

    assert "are worth" not in text.split("Confidence:\n")[0]
    assert "joint-saving" not in [f["id"] for f in data["findings"]]


def test_severity_marks_the_hedged_conclusions_as_such():
    """A build that failed is not the same kind of statement as a run
    being incremental, and a machine should not have to read the prose to
    tell them apart."""
    by_id = findings_by_id(compute_findings(_real_shaped_result()))

    assert by_id["time-concentration"]["severity"] == "high"
    assert by_id["run-mode-incremental"]["severity"] == "info"
    assert by_id["mesh-graph"]["severity"] == "info"


def test_a_failed_build_is_the_first_finding_and_is_critical():
    """`UX-54`: said before any efficiency number, because every number
    below describes a build that did not finish."""
    result = _real_shaped_result()
    result.violations = [{"type": "build_failed", "failed_count": 4,
                          "failed_elements": ["a.bst", "b.bst"]}]
    findings = compute_findings(result)

    assert findings[0]["id"] == "build-failed"
    assert findings[0]["severity"] == "critical"
    assert findings[0]["elements"] == ["a.bst", "b.bst"]
