"""UX-194: hand the timeline to ui.perfetto.dev, wholesale.

Direction 7's timeline rule: none of our own, ever. The mechanics are
Perfetto's documented deep-link handshake - open the UI, ping until it
answers `PONG`, post the buffer once - and the whole of it is ~30 lines
that never touch a server.

**It is not an upload**, and the page says so, because it looks exactly
like one: a public URL opens and your build data appears in it. The
bytes cross tab-to-tab through `postMessage`; ui.perfetto.dev is a
static site with nowhere to send a trace to. A guard below asserts the
page keeps saying it.

The handshake is driven by a scripted `window` double under Node, so
what is tested is the shipped `perfetto.js` and CI needs no browser.
"""
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request

import pytest

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

_WRAPPED = """[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst
[wrapper][2026-08-21 12:00:00,100] INFO: [00:00:00][aaaaaaaa][   build:work-a.bst] START Building
[wrapper][2026-08-21 12:00:03,100] INFO: [00:00:03][aaaaaaaa][   build:work-a.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:03,200] INFO: Return code: 0
"""
_RAW = """START pid=101 ppid=1 ts=1000.000000 element=work-a.bst cmd=cc -c main.c
END pid=101 ppid=1 ts=1002.500000 element=work-a.bst cmd=cc -c main.c
"""


@pytest.fixture
def snapshot(tmp_path):
    """A snapshot with both planes, so there is a timeline to hand over."""
    snap = tmp_path / "20260821T120000Z"
    snap.mkdir()
    (snap / "build.log").write_text(_WRAPPED)
    shutil.copytree(GOLDEN, snap / "run")
    os.remove(snap / "run" / "expected_output.json")
    with gzip.open(snap / "plane2.log.gz", "wt") as handle:
        handle.write(_RAW)
    return snap


@pytest.fixture
def served():
    from tools.bga_view import serve

    made = []

    def start(run, **kwargs):
        httpd, url = serve(str(run), **kwargs)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        made.append(httpd)
        return url

    yield start
    for httpd in made:
        httpd.shutdown()
        httpd.server_close()


def _get(url):
    with urllib.request.urlopen(url, timeout=15) as response:
        return response.status, response.headers, response.read()


class TestTheServedTrace:
    def test_it_is_bga_timelines_output_verbatim(self, snapshot, served):
        """Digest-compared, because "the same trace" is the whole claim:
        the viewer must not acquire a renderer of its own."""
        from tools.bga_timeline import render
        from tools.bga_view import TRACE_NAME

        _, _, body = _get(served(snapshot / "run") + TRACE_NAME)
        scratch = tempfile.mkdtemp()
        try:
            direct = os.path.join(scratch, "t.json")
            render(str(snapshot), direct, quiet=True)
            expected = open(direct, "rb").read()
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

        assert hashlib.sha256(gzip.decompress(body)).hexdigest() == \
            hashlib.sha256(expected).hexdigest()

    def test_it_is_served_gzipped_and_stays_that_way(self, snapshot, served):
        """Not `Content-Encoding: gzip`: the page hands the *compressed*
        bytes to Perfetto, which sniffs gzip itself. A transparently
        decoding fetch would undo the win."""
        from tools.bga_view import TRACE_NAME

        _, headers, body = _get(served(snapshot / "run") + TRACE_NAME)
        assert headers["Content-Type"] == "application/gzip"
        assert headers.get("Content-Encoding") is None
        assert body[:2] == b"\x1f\x8b", "not gzip"
        assert len(body) < len(gzip.decompress(body))

    def test_a_run_with_no_timeline_says_so_rather_than_serving_nothing(
            self, tmp_path, served):
        """An extracted run, a fetched capture, or `--no-keep-raw`."""
        from tools.bga_view import TRACE_NAME

        run = tmp_path / "run"
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        url = served(run)

        meta = json.loads(_get(url + "run.json")[2])
        assert meta["has_timeline"] is False
        with pytest.raises(urllib.error.HTTPError) as caught:
            _get(url + TRACE_NAME)
        assert caught.value.code == 404

    def test_the_render_leaves_no_scratch_path_on_stderr(self, snapshot):
        """`UX-197` item 2, one command over. `bga view` renders into a
        temporary directory it deletes; the converter's own "Wrote N
        events to <path>" named that path. Reproduced here before the
        fix as `Wrote 11 trace events to /tmp/bga-view-XXXX/...`."""
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys\n"
             "from tools.bga_view import trace_bytes\n"
             "sys.stdout.write(str(len(trace_bytes(%r) or b'')))"
             % str(snapshot / "run")],
            capture_output=True, text=True, cwd=os.getcwd())
        assert result.returncode == 0, result.stderr
        assert int(result.stdout) > 0, "nothing was rendered"
        assert "/tmp/" not in result.stderr, result.stderr
        assert "Wrote" not in result.stderr, result.stderr


@needs_node
class TestTheHandshake:
    """Perfetto's deep-link protocol, driven by a scripted window."""

    def _run(self, script):
        result = subprocess.run(
            [node, "--input-type=module", "-e", _HARNESS % script],
            capture_output=True, text=True, cwd=os.getcwd(), timeout=60)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_it_pings_until_pong_then_posts_the_buffer_once(self):
        out = self._run("await scenario({ pongAfterPings: 3 });")
        assert out["error"] is None, out["error"]
        assert out["pings"] >= 3, out
        assert len(out["posted"]) == 1, "the trace was posted more than once"
        assert out["posted"][0]["perfetto"]["title"] == "bga timeline"
        assert out["posted"][0]["bytes"] == 5

    def test_the_bytes_arrive_unchanged(self):
        out = self._run("await scenario({ pongAfterPings: 1 });")
        assert out["posted"][0]["contents"] == [1, 2, 3, 4, 5]

    def test_it_stops_pinging_once_it_has_handed_over(self):
        out = self._run("await scenario({ pongAfterPings: 2, settleMs: 40 });")
        assert out["pingsAfterHandover"] == 0, (
            "it kept pinging a tab that already has the trace")

    def test_a_message_from_another_origin_does_not_trigger_the_handover(self):
        """What the origin check actually buys - established by
        falsifying the first version of this test, which stayed green
        with the check deleted.

        It is **not** confidentiality: `tab.postMessage(msg, origin)`
        names Perfetto's origin as the only acceptable target, so the
        bytes cannot be delivered anywhere else whatever answers. What
        the check prevents is firing *early*: a stray `PONG` from any
        other frame would make this post the buffer before Perfetto's
        worker is up, and Perfetto would simply never receive the trace
        - a silent empty tab, which is the failure mode hardest to
        diagnose.

        So: an imposter answers and the real origin never does. Nothing
        may be posted.
        """
        out = self._run(
            "await scenario({ pongAfterPings: null, imposterAfterPings: 2 });")
        assert out["posted"] == [], (
            "a PONG from another origin triggered the handover")
        assert out["error"], "it should still be waiting, then time out"

    def test_a_blocked_popup_is_an_explained_failure(self):
        out = self._run("await scenario({ blockPopup: true });")
        assert out["error"], "a blocked pop-up resolved successfully"
        assert "pop-up" in out["error"]
        assert "ui.perfetto.dev" in out["error"], (
            "the message should name the manual route out")

    def test_a_tab_that_never_answers_times_out_rather_than_hanging(self):
        out = self._run("await scenario({ pongAfterPings: null, "
                        "runTimeout: true });")
        assert out["error"] and "did not answer" in out["error"]


class TestThePagesSayWhatIsHappening:
    def test_the_handoff_page_says_it_is_not_an_upload(self):
        text = open("bga/viewer/perfetto.html", encoding="utf-8").read()
        assert "Nothing is uploaded" in text
        assert "tab to tab" in text.lower() or "tab-to-tab" in text.lower()

    def test_it_offers_a_way_out_when_the_popup_is_blocked(self):
        text = open("bga/viewer/perfetto.html", encoding="utf-8").read()
        assert "timeline.json.gz" in text, "no download fallback"
        assert "ui.perfetto.dev" in text

    def test_the_module_says_it_too_where_a_maintainer_reads(self):
        text = open("bga/viewer/perfetto.js", encoding="utf-8").read()
        assert "not an upload" in text.lower()


class TestTheCannedSql:
    """Item 3: a docs page served by view, not a feature."""

    def test_every_snippet_is_a_select_that_parses(self):
        import re
        import sqlite3

        text = open("bga/viewer/sql.html", encoding="utf-8").read()
        snippets = re.findall(r"<pre><code>(.*?)</code></pre>", text, re.S)
        assert len(snippets) >= 4, f"only {len(snippets)} snippets"
        for snippet in snippets:
            query = (snippet.replace("&gt;", ">").replace("&lt;", "<")
                     .replace("&amp;", "&"))
            assert query.strip().lower().startswith("select")
            # PerfettoSQL is SQLite-dialect; `sqlite3.complete_statement`
            # plus an EXPLAIN against the real parser is as far as this
            # can go without trace_processor, and it does catch a typo.
            assert sqlite3.complete_statement(query), query[:60]

    def test_each_one_says_what_it_answers(self):
        import re

        text = open("bga/viewer/sql.html", encoding="utf-8").read()
        blocks = re.findall(r"<h2>(.*?)</h2>\s*<p class=\"muted\">(.*?)</p>",
                            text, re.S)
        assert len(blocks) >= 4
        for heading, why in blocks:
            assert heading.strip().endswith("?"), heading
            assert len(why.strip()) > 40, heading

    def test_it_is_reachable_from_the_handoff_page(self, snapshot, served):
        assert _get(served(snapshot / "run") + "sql.html")[0] == 200

    @pytest.mark.skipif(shutil.which("trace_processor_shell") is None,
                        reason="trace_processor_shell is not installed")
    def test_the_snippets_run_against_a_real_trace(self, snapshot):  # pragma: no cover
        """Local only, deliberately: bundling Perfetto is out of scope,
        and a CI job that downloads it would be a network dependency for
        a docs page."""
        import re

        from tools.bga_timeline import render

        scratch = tempfile.mkdtemp()
        trace = os.path.join(scratch, "t.json")
        render(str(snapshot), trace, quiet=True)
        text = open("bga/viewer/sql.html", encoding="utf-8").read()
        for snippet in re.findall(r"<pre><code>(.*?)</code></pre>", text, re.S):
            query = snippet.replace("&gt;", ">").replace("&lt;", "<")
            result = subprocess.run(
                ["trace_processor_shell", "-q", "/dev/stdin", trace],
                input=query, capture_output=True, text=True, timeout=120)
            assert result.returncode == 0, result.stderr


class TestTheCommandLine:
    def test_perfetto_lands_on_the_handoff_page(self, snapshot, monkeypatch):
        import tools.bga_view as view

        opened = []
        monkeypatch.setattr(view.webbrowser, "open", opened.append)
        monkeypatch.setattr(view.http.server.ThreadingHTTPServer,
                            "serve_forever", lambda self: None)
        code = view.main([str(snapshot / "run"), "--perfetto"])
        assert code == 0
        assert opened and opened[0].endswith("/perfetto.html"), opened

    def test_a_run_with_no_timeline_refuses_with_the_signal_code(
            self, tmp_path, capsys):
        """Exit 7 - `UX`'s "signal unavailable" - rather than opening a
        page that would say "404" in the browser."""
        import tools.bga_view as view

        run = tmp_path / "run"
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        assert view.main([str(run), "--perfetto", "--no-browser"]) == 7
        assert "no timeline" in capsys.readouterr().err

    def test_the_help_is_still_under_the_cap(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main(['view','--help']))"],
            capture_output=True, text=True, cwd=os.getcwd())
        assert len(result.stdout.splitlines()) <= 45, result.stdout


class TestTheFormatDecisionIsWrittenDown:
    """Item 4: the next person reaching for protobuf should find the
    argument, not an accident."""

    def test_direction_7_records_it_with_a_revisit_trigger(self):
        text = open("docs/design/directions.md", encoding="utf-8").read()
        assert "legacy Chrome JSON" in text or "legacy chrome json" in text.lower()
        assert "protobuf" in text.lower()

    def test_the_timeline_docs_point_at_the_argument(self):
        text = open("docs/guides/cli.md", encoding="utf-8").read()
        assert "ui.perfetto.dev" in text


# A scripted `window`: `perfetto.js` takes its whole environment through
# `deps`, so the handshake runs under plain Node with no DOM at all.
_HARNESS = """
const { openInPerfetto, PERFETTO_ORIGIN } = await import("./bga/viewer/perfetto.js");

globalThis.scenario = async function ({
  pongAfterPings = 1, blockPopup = false, imposterAfterPings = null,
  settleMs = 0, runTimeout = false,
  imposterOrigin = "https://evil.example",
}) {
  const out = { pings: 0, posted: [], pingsAfterHandover: 0, error: null };
  let handedOver = false;
  const listeners = [];

  const tab = {
    postMessage(message, origin) {
      if (message === "PING") {
        out.pings += 1;
        if (handedOver) { out.pingsAfterHandover += 1; return; }
        if (imposterAfterPings !== null && out.pings >= imposterAfterPings) {
          // A frame that is not Perfetto answering the ping.
          listeners.forEach((fn) => fn({ origin: imposterOrigin, data: "PONG" }));
        }
        if (pongAfterPings !== null && out.pings >= pongAfterPings) {
          listeners.forEach((fn) => fn({ origin: PERFETTO_ORIGIN, data: "PONG" }));
        }
        return;
      }
      handedOver = true;
      const view = new Uint8Array(message.perfetto.buffer);
      out.posted.push({ perfetto: { title: message.perfetto.title },
                        bytes: view.length, contents: [...view] });
    },
  };

  const deps = {
    open: () => (blockPopup ? null : tab),
    addEventListener: (_name, fn) => listeners.push(fn),
    removeEventListener: (_name, fn) => {
      const i = listeners.indexOf(fn); if (i >= 0) listeners.splice(i, 1);
    },
    setInterval: (fn) => { const id = setInterval(fn, 1); return id; },
    clearInterval: (id) => clearInterval(id),
    // The real 20s timeout would make this test take 20s.
    setTimeout: (fn) => setTimeout(fn, runTimeout ? 30 : 1e9),
    clearTimeout: (id) => clearTimeout(id),
  };

  try {
    // A wall-clock backstop, separate from the handshake's own timeout:
    // a mutation that removes the `resolve` leaves the promise pending
    // forever, and without this the guard hangs instead of failing.
    // Found exactly that way, falsifying P1.
    await Promise.race([
      openInPerfetto(new Uint8Array([1, 2, 3, 4, 5]).buffer, "bga timeline", deps),
      new Promise((_, reject) => setTimeout(
        () => reject(new Error("the handshake never settled")), 1200)),
    ]);
  } catch (error) {
    out.error = String(error.message ?? error);
  }
  if (settleMs) await new Promise((r) => setTimeout(r, settleMs));
  console.log(JSON.stringify(out));
  // Explicit: in the scenarios where the handshake never settles, its
  // ping interval and long timeout are still pending, and node keeps
  // the event loop alive on them. Without this the guard times out at
  // the subprocess level instead of failing on its assertion.
  process.exit(0);
};

%s
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
