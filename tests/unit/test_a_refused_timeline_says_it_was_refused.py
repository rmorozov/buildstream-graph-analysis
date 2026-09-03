"""UX-545: an export that refused the timeline told the reader it had no log.

`export()` writes `timeline_omitted` when every rung of `UX-530`'s
ladder is over a ceiling. Nothing in `bga/viewer/` read it, so the page
fell through to `renderQuestions`'s no-timeline branch:

```text
This snapshot carries no build log, so there is no timeline to open here
```

False twice - the snapshot has one, and capturing again refuses again.

**Two states, and the discrimination is the guard.** `export()` writes
`timeline_recipe` only for a timeline it rendered and refused, so a
refusal and a run that never captured Plane 2 are told apart by what the
export already publishes rather than by a new flag. Both directions are
booted: a page that says "refused" for the absent case has not
discriminated, and would pass a one-sided guard.

The instrument is the **exported page**, booted through the shared probe
(`test_a_report_you_can_navigate.py`'s `_PROBE`, extended by one read),
not `renderQuestions` called with literals - a probe that hands the
options in itself restates `app.js`'s wiring, and stays green when the
wiring is what breaks.

The ceiling is lowered rather than the fixture grown: `UX-430` measured
where it belongs and this item's Out of Scope is that it stays there.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages                                       # noqa: E402

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: The sentence that was wrong, read out of the module that writes it,
#: so a reword is a failure here rather than a guard that stops looking.
QUESTIONS = (REPO / "bga/viewer/questions.js").read_text(encoding="utf-8")
NO_LOG = "This snapshot carries no build log"

#: `UX-545`'s addition to the shared probe: the sentence the booted page
#: actually leaves the reader with, and the flag beside it. `report` is
#: the probe's own root - the node `app.js` renders into - and this
#: prints a second JSON line beside the probe's.
_TAIL = """
const findNode = (n, pred) => {
  if (!n) return null;
  if (pred(n)) return n;
  for (const c of n.children ?? []) {
    const hit = findNode(c, pred);
    if (hit) return hit;
  }
  return null;
};
const questions = findNode(
  report, (n) => n.attrs?.["data-section"] === "perfetto-questions");
const lead = questions && findNode(questions, (n) => n.tagName === "p");
console.log(JSON.stringify({
  section: Boolean(questions),
  lead: lead ? lead.textContent : null,
  omitted: lead ? (lead.attrs["data-omitted"] ?? null) : null,
}));
"""


def _probe_source():
    """The shared boot, reused rather than re-implemented (`UX-235`).

    A second copy of the preamble is a second model of the browser; the
    shim is imported by the probe and this only appends a read to it.
    """
    source = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text(
        encoding="utf-8")
    return source.split('_PROBE = r"""', 1)[1].rsplit('"""', 1)[0] + _TAIL


def _boot(page):
    """Boot the exported page and return its questions lead."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    html = pathlib.Path(page).read_text(encoding="utf-8")
    module = tmp / "inline.mjs"
    module.write_text(
        re.search(r'<script type="module">(.*?)</script>', html, re.S).group(1),
        encoding="utf-8")
    probe = tmp / "probe.mjs"
    probe.write_text(_probe_source(), encoding="utf-8")
    result = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=REPO,
        timeout=90,
        env=dict(os.environ, PAGE=str(page), MOD=str(module),
                 PROTOCOL="file:",
                 BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs")))
    assert result.returncode == 0, result.stderr[-3000:]
    lines = result.stdout.strip().splitlines()
    booted = json.loads(lines[-2])
    assert booted["error"] is None, booted["error"]
    read = json.loads(lines[-1])
    assert read["section"], "the questions section did not render"
    return read


@pytest.fixture(scope="module")
def refused(tmp_path_factory):
    """A two-plane capture over **both** rungs, exported.

    `TRACE_TRACK_BUDGET` is set one track under what `--planes 1`
    draws, so the whole timeline and the narrowed one are both over it
    and `export()` reaches its refusal.
    """
    from tools import bga_view as view
    from tools.bga_timeline import PLANE1_ONLY, render

    into = tmp_path_factory.mktemp("refused")
    run = pages.two_plane_snapshot(into)
    narrowed = render(str(run.parent), str(into / "probe1.pftrace"),
                      planes=PLANE1_ONLY, quiet=True)
    ceiling = narrowed["tracks"] - 1
    page = into / "report.html"
    before = view.TRACE_TRACK_BUDGET
    view.TRACE_TRACK_BUDGET = ceiling
    try:
        view.export(str(run), str(page))
    finally:
        view.TRACE_TRACK_BUDGET = before
    payload = json.loads(re.search(
        r'id="bga-run">(.*?)</script>',
        page.read_text(encoding="utf-8"), re.S).group(1))
    return {"page": page, "payload": payload, "run": run,
            "tracks": narrowed["tracks"], "ceiling": ceiling}


@pytest.fixture(scope="module")
def absent(tmp_path_factory):
    """The other state: a run that captured no Plane 2 at all."""
    from tools import bga_view as view

    into = tmp_path_factory.mktemp("absent")
    run = into / "run"
    shutil.copytree(pages.FIXTURES["golden"], run,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (run / "expected_output.json").unlink(missing_ok=True)
    page = into / "report.html"
    view.export(str(run), str(page))
    payload = json.loads(re.search(
        r'id="bga-run">(.*?)</script>',
        page.read_text(encoding="utf-8"), re.S).group(1))
    return {"page": page, "payload": payload}


class TestTheExportPublishesTheRefusal:
    """What the page is given. `UX-530` measured the rung above this."""

    def test_both_rungs_refuse_and_the_ceiling_is_named(self, refused):
        payload = refused["payload"]
        assert payload["has_timeline"] is False, payload
        said = payload["timeline_omitted"]
        assert "the whole timeline" in said, said
        assert "--planes 1" in said, (
            f"the narrowed rung was not tried or not reported: {said}")
        assert f"{refused['ceiling']:,}-track ceiling" in said, said
        assert payload["timeline_recipe"]["command"].endswith("--perfetto")

    def test_a_run_with_no_plane_2_gets_no_recipe(self, absent):
        """The key the page discriminates on. If the absent run carried
        a recipe too, the reader below would be told both were refusals
        and this file would prove nothing."""
        payload = absent["payload"]
        assert payload["has_timeline"] is False, payload
        assert "timeline_recipe" not in payload, payload["timeline_recipe"]
        assert payload["timeline_omitted"]


class TestTheServedPageIsNotToldItWasRefused:
    """The acceptance's other half. `UX-296` keeps the render off the
    startup path, so the server never meets a ceiling: the same capture
    served has its timeline, and the refusal is a fact about the file."""

    def test_the_same_capture_served_still_offers_the_timeline(self, refused):
        import json as _json
        import threading
        import urllib.request

        from tools.bga_view import serve

        httpd, url = serve(str(refused["run"]), port=0)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            with urllib.request.urlopen(url.rstrip("/") + "/run.json",
                                        timeout=30) as response:
                run_json = _json.loads(response.read().decode("utf-8"))
        finally:
            httpd.shutdown()
            httpd.server_close()
        assert run_json["has_timeline"] is True, run_json
        assert "timeline_omitted" not in run_json
        assert "timeline_recipe" not in run_json


@needs_node
class TestThePageNamesTheRefusal:

    def test_the_refused_page_says_what_it_refused_and_what_to_run(
            self, refused):
        read = _boot(refused["page"])
        lead = read["lead"]
        assert NO_LOG not in lead, (
            f"a refusal is still told it has no build log: {lead}")
        assert refused["payload"]["timeline_omitted"] in lead, (
            f"the refusal did not reach the page in its own words: {lead}")
        assert f"{refused['ceiling']:,}-track ceiling" in lead, lead
        assert refused["payload"]["timeline_recipe"]["command"] in lead, lead
        assert read["omitted"] == "refused", read

    def test_a_capture_free_run_still_gets_the_capture_sentence(self, absent):
        """The direction that discriminates. A page that says "refused"
        for a snapshot that never captured Plane 2 has swapped one false
        sentence for another."""
        read = _boot(absent["page"])
        lead = read["lead"]
        assert NO_LOG in lead, lead
        assert "refused" not in lead, lead
        assert read["omitted"] is None, read


def test_the_sentence_the_guard_reads_is_the_one_the_page_writes():
    """`NO_LOG` above is a literal; this is what stops it going stale."""
    assert NO_LOG in QUESTIONS


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
