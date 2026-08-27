"""UX-334: nothing in this repository was listening to the console.

The user's field report was that the Chrome console on `bga view` is
full of Content-Security-Policy violations. It was, and it had been for
ten rounds, because **every guard here reads the DOM and none of them
read what the browser said about it**. A page can render every section
correctly, pass every geometry walk, and still tell its reader on each
boot that three stylesheets were refused and four files are missing.

So this is not a fix's test. It is the net for the class: any
error-severity console message, any `securitypolicyviolation`, and the
form-control complaints the Issues panel raises, on **both** fixture
runs in **both** shapes the report is read in - served over the local
http server, and exported to one file opened from disk. A `TypeError`
thrown during boot lands here too, which is why `UX-335`'s class needs
no second instrument.

**What was measured before the fix** (golden fixture, headless
Chromium 141, this harness):

```text
                      exported            served
console errors        6                   7
csp violations        0                   3   style-src-attr
issues              144                  83
  form control      138 + 6 label        70 + 10 label
```

and the three classes behind those numbers, each named below as a
regression case:

* `style-src-attr` - `drawings.js` set an exhibit tick's `left:`
  through a **style attribute**, which `default-src 'self'` forbids.
  Enforced, not reported: every tick computed `left: 0px` and piled at
  the axis origin on the served page, while the export - which has no
  CSP - drew them where they belong. A drawing that is right in one
  shape and wrong in the other, invisibly.
* the optional-payload probes - `compare`, `store` and
  `store-aggregate` are absent on an ordinary run, and the page learned
  that by fetching each one and catching the failure. 404s served, CORS
  refusals on `file://`.
* `/favicon.ico` - asked for by the browser on every navigation whether
  a document links one or not.

**What it cannot see**, said rather than implied: a machine with no
Chrome (these skip, and the skip is in `tests/conftest.py`'s census),
and any page state a boot does not reach - a filter typed, a fold
opened, a hand-off clicked. This is the boot, on two runs, in two
shapes.
"""
import pathlib
import shutil
import sys
import threading
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"
MACRO = REPO / "tests/fixtures/macro_micro/run"

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
needs_node = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node is not installed")

#: The Issues-panel codes this item closed. Named rather than "no
#: issues at all": a browser version that grows a new advisory must
#: redden the round it appears in, in a guard that says which advisory
#: - not this one, silently, for a reason nobody can read.
FORM_ISSUES = ("FormEmptyIdAndNameAttributesForInputError",
               "FormLabelHasNeitherForNorNestedInput")

#: Console levels that are a defect. `warning` is not: a browser warns
#: about deprecations on its own schedule, and a guard that fails on
#: those fails on a Chrome upgrade rather than on a change here.
BAD_LEVELS = ("error", "assert")


def _boot(run_dir, out_dir):
    """The two shapes of one run: `(exported file url, served url)`."""
    from tools.bga_view import export, serve

    run = out_dir / "run"
    shutil.copytree(run_dir, run)
    (run / "expected_output.json").unlink(missing_ok=True)
    page = out_dir / "report.html"
    export(str(run), str(page))

    httpd, url = serve(str(run), port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return page.as_uri(), url, httpd


@pytest.fixture(scope="module")
def observed(tmp_path_factory):
    """`{page name: observation}` for four boots, one browser."""
    if chrome is None or shutil.which("node") is None:    # pragma: no cover
        pytest.skip(NO_BROWSER)
    servers, urls = [], {}
    for name, run in (("golden", GOLDEN), ("macro_micro", MACRO)):
        exported, served, httpd = _boot(run, tmp_path_factory.mktemp(name))
        servers.append(httpd)
        urls[f"{name} exported"] = exported
        urls[f"{name} served"] = served
    # The server is a thread in this process and the browser is another
    # process: a moment between binding and the first request is not
    # worth a readiness protocol.
    time.sleep(0.3)
    try:
        with Browser(chrome) as opened:
            yield {name: opened.observe(url) for name, url in urls.items()}
    finally:
        for httpd in servers:
            httpd.shutdown()


def _errors(observation):
    return [entry for entry in observation["console"]
            if entry["level"] in BAD_LEVELS]


@needs_browser
@needs_node
class TestTheConsoleStaysClean:
    def test_no_page_logs_an_error(self, observed):
        """Every channel the console has: `console.error`, an uncaught
        exception, and what the *browser* says about the page - which
        is where a 404 on a subresource is reported and nowhere else.
        """
        for name, got in observed.items():
            bad = _errors(got)
            assert not bad, (name, [f"{e['source']}: {e['text'][:200]}"
                                    for e in bad])

    def test_no_page_violates_its_own_policy(self, observed):
        """`securitypolicyviolation`, collected in the page.

        Separate from the console on purpose: a violation is *also*
        logged, but the event carries the directive that refused it -
        `style-src-attr`, not a paragraph - and a directive is what a
        reader needs to find the line.
        """
        for name, got in observed.items():
            assert not got["csp"], (name, got["csp"])

    def test_the_style_attribute_path_stays_shut(self, observed):
        """The regression case by name.

        `drawings.js` drew tick labels with a `style:` attribute, which
        this server's `default-src 'self'` **enforces** against - so the
        served page lost the geometry the export kept. A CSSOM
        assignment is not an inline style and is allowed; the attribute
        is the whole defect, and this clause is what keeps a future
        drawing from reaching for it again.
        """
        for name, got in observed.items():
            attrs = [v for v in got["csp"]
                     if "style" in (v.get("directive") or "")]
            assert not attrs, (name, attrs)

    def test_no_payload_is_discovered_by_failing_to_fetch_it(self, observed):
        """`compare`, `store`, `store-aggregate` - and the favicon.

        The manifest says which payloads exist (`_offered` in
        `bga_view.py`), so the page asks it rather than the network. A
        regression here shows up as a 404 or a CORS refusal naming the
        payload, which is what this reads for - the general clause
        above would catch it too, and this one says *which*.
        """
        for name, got in observed.items():
            # Text *and* url: a served 404 says only "Failed to load
            # resource: ... 404" and carries the path in its own field,
            # while a `file://` refusal names the path in the sentence.
            # Reading the text alone made this clause blind to exactly
            # half the regression it is named for - found by mutation,
            # not by review.
            probes = [f"{e['text']} {e['url']}" for e in _errors(got)
                      if any(word in f"{e['text']} {e['url']}" for word in
                             ("compare.json", "store.json",
                              "store-aggregate.json", "favicon.ico"))]
            assert not probes, (name, probes)

    def test_every_form_control_has_an_identity(self, observed):
        """The Issues panel's two form complaints, at zero.

        138 and 6 on the exported golden page before this; 70 and 10 on
        the served one. An `aria-label` answers neither - six were
        already there, on these very controls.
        """
        for name, got in observed.items():
            forms = [i for i in got["issues"] if i["reason"] in FORM_ISSUES]
            assert not forms, (name, forms)


@needs_browser
@needs_node
class TestTheInstrumentCanSee:
    """A net that catches nothing is indistinguishable from a clean
    page. These fail if the harness has gone deaf, which is the way a
    guard like this dies quietly.
    """

    def test_it_reports_a_console_error_that_is_there(self, observed,
                                                      tmp_path_factory):
        out = tmp_path_factory.mktemp("positive")
        exported, served, httpd = _boot(GOLDEN, out)
        try:
            with Browser(chrome) as opened:
                got = opened.observe(
                    exported, 'console.error("UX-334 positive control"), 1')
        finally:
            httpd.shutdown()
        texts = [e["text"] for e in _errors(got)]
        assert any("UX-334 positive control" in t for t in texts), texts

    def test_it_reports_a_browser_log_line_that_is_there(self, observed,
                                                        tmp_path_factory):
        """The third channel, and the one with no other witness.

        A 404 on a subresource is reported by the *browser*, not by the
        page - `Log.entryAdded` and nowhere else. Found by mutation:
        dropping `Log.enable` from the harness and reintroducing the
        favicon 404 left all seven clauses green, so the whole
        network-error half of this guard could have been switched off
        without a single test noticing.
        """
        out = tmp_path_factory.mktemp("positive-log")
        exported, served, httpd = _boot(GOLDEN, out)
        try:
            with Browser(chrome) as opened:
                got = opened.observe(
                    served,
                    'fetch("ux-334-no-such-payload.json").then(() => 1,'
                    ' () => 1)')
        finally:
            httpd.shutdown()
        network = [f"{e['text']} {e['url']}" for e in _errors(got)
                   if "ux-334-no-such-payload" in e["url"]]
        assert network, [e["text"] for e in got["console"]]

    def test_it_reports_a_policy_violation_that_is_there(self, observed,
                                                        tmp_path_factory):
        """The served page, and an inline style set the way the fix
        stopped setting it. If this passes and the clauses above pass,
        the page is clean; if this fails, they prove nothing."""
        out = tmp_path_factory.mktemp("positive-csp")
        exported, served, httpd = _boot(GOLDEN, out)
        try:
            with Browser(chrome) as opened:
                got = opened.observe(
                    served,
                    'document.body.setAttribute("style", "color: red"), 1')
        finally:
            httpd.shutdown()
        directives = [v.get("directive") for v in got["csp"]]
        assert any("style" in (d or "") for d in directives), (
            got["csp"], _errors(got))
