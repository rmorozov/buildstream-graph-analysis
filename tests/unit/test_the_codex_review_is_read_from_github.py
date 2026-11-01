"""`UX-1369`: a Codex review is read from what the bot submitted, not from its marker.

holds: rules.md#some-claims-have-no-local-instrument-open-the-pr-first-7-marked-ready-the-round-pr-gets-one-codex-review-and-each-finding-is-answered-like-a-hold-procedure-codex-reviews-md
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools import dev_codex_status as codex

BOT = codex.BOT
HEAD = "d9dc9706fe860efdc22bcdc1d2800d7cd502b4fb"
OLD = "1111111111111111111111111111111111111111"
# #338's summary comment as GitHub served it after the review was submitted.
STALE = (
    "<!-- codex-review-state:v1 "
    '{"code_review":{"commit_sha":"' + HEAD + '","has_any_findings":null,'
    '"has_unresolved_findings":null,"status":"running"},"security_review":'
    '{"commit_sha":null,"has_any_findings":null,"has_unresolved_findings":null,"status":null}} -->'
)


def _user(login):
    return {"login": login}


def _finding(id_, reply_to=None, login=BOT):
    return {
        "id": id_,
        "in_reply_to_id": reply_to,
        "user": _user(login),
        "path": "docs/contributing/codex-reviews.md",
        "line": 13,
        "html_url": f"https://example.invalid/{id_}",
    }


def _verdict(shas, findings=(), changed=()):
    return codex.verdict(HEAD, list(shas), list(findings), lambda _sha: list(changed))


def test_a_submitted_review_is_done_though_the_marker_says_running():
    reviews = [{"user": _user(BOT), "commit_id": HEAD}]
    assert codex.marker([{"user": _user(BOT), "body": STALE}])["code_review"]["status"] == "running"
    assert _verdict(codex.reviewed_shas(reviews, [])) == ([], [])


def test_a_plus_one_reaction_is_a_review_with_no_findings():
    reactions = [{"user": _user(BOT), "content": "+1"}, {"user": _user("someone"), "content": "+1"}]
    assert codex.reviewed_shas([], reactions) == ["+1"]
    assert codex.reviewed_shas([], reactions[1:]) == []


def test_no_review_fails():
    problems, _ = _verdict([])
    assert len(problems) == 1


def test_only_code_after_the_reviewed_sha_asks_for_another_review():
    assert _verdict([OLD], changed=["docs/audits/round-176.md", "tests/quality_baseline.json"])[0] == []
    problems, _ = _verdict([OLD], changed=["bga/report/json.py"])
    assert problems and "bga/report/json.py" in problems[0]


def test_a_finding_is_open_until_a_reply_answers_it():
    answered = [_finding(1), _finding(2, reply_to=1, login="rmorozov")]
    assert codex.open_findings(answered) == []
    assert [f["id"] for f in codex.open_findings([_finding(3)])] == [3]


def test_a_boundary_wants_a_security_review_and_its_absence_is_a_note():
    assert "security review wanted" in codex.security_note(["bga/viewer/app.js"], security_done=False)
    assert codex.security_note(["bga/report/json.py"], security_done=False) is None
    assert codex.security_note(["bga/viewer/app.js"], security_done=True) is None
