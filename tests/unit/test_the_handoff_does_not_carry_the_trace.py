"""UX-299: above a size, the trace is fetched rather than carried.

`UX-198` built the tab-to-tab handoff and measured it at 25 KB, where
it is exactly right. It is the same design at 1.5 GB, where the report
tab meets the memory wall the server met in `UX-296`: `arrayBuffer()`
materialises the whole response, `postMessage` structured-clones it,
and Perfetto decompresses a third copy in its own tab - three copies
before the first pixel.

The `?url=` deep link already exists as the fallback, and at scale the
roles invert: Perfetto fetching the trace from this server itself has
none of those copies. So one threshold decides which transport is used,
and the same threshold decides whether `--export` inlines the trace at
all - because "a `data:` URL of gigabytes" and "a `postMessage` of
gigabytes" are the same mistake wearing two hats.

**The size cannot be known when the page loads.** Finding it means
rendering the trace, which `UX-296` deliberately moved off the startup
path. So the page asks for the headers - a `HEAD`, reading no trace
bytes - at the moment the reader asks for the timeline, and picks the
transport from `Content-Length`.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Enough DOM to run `wireTheHandoff` for real *and fire its click*: the
# earlier harness stubbed `addEventListener` away, which is why nothing
# had ever driven the handler itself.
_HARNESS = """
const size = %(size)s;
const inlineMax = %(inline_max)s;
const here = %(here)s;

const calls = { fetches: [], opened: [], navigated: [], posted: 0, closed: 0 };

function node(id) {
  const listeners = {};
  return {
    id, hidden: true, href: "", textContent: "", parentElement: null,
    children: [], listeners,
    addEventListener(name, fn) { (listeners[name] ??= []).push(fn); },
  };
}
const nodes = {
  actions: node("actions"),
  perfetto: node("perfetto"),
  handoff: node("handoff"),
  "perfetto-link": node("perfetto-link"),
  "actions-fallback": node("actions-fallback"),
  "trace-download": node("trace-download"),
  "actions-download": node("actions-download"),
  "bga-trace": { textContent: here + "timeline.json.gz" },
};
nodes["perfetto-link"].parentElement = nodes["actions-fallback"];
nodes["trace-download"].parentElement = nodes["actions-download"];

globalThis.document = { getElementById: (id) => nodes[id] ?? null };
globalThis.location = { href: here + "index.html" };

globalThis.fetch = async (url, init = {}) => {
  calls.fetches.push({ url: String(url), method: init.method ?? "GET" });
  if ((init.method ?? "GET") === "HEAD") {
    return { ok: true, headers: { get: (k) =>
      k.toLowerCase() === "content-length" ? String(size) : null } };
  }
  return {
    ok: true,
    headers: { get: () => null },
    arrayBuffer: async () => new Uint8Array([1, 2, 3, 4, 5]).buffer,
  };
};

const tab = {
  set location(value) { calls.navigated.push(String(value)); },
  postMessage(message) {
    if (message === "PING") {
      (globalThis.__listeners ?? []).forEach(
        (fn) => fn({ origin: "https://ui.perfetto.dev", data: "PONG" }));
      return;
    }
    calls.posted += 1;
  },
  close() { calls.closed += 1; },
};
globalThis.__listeners = [];
globalThis.window = {
  open(url) { calls.opened.push(String(url)); return tab; },
  addEventListener(name, fn) {
    if (name === "message") globalThis.__listeners.push(fn);
  },
  removeEventListener() {},
};
globalThis.addEventListener = globalThis.window.addEventListener;
globalThis.removeEventListener = () => {};

const { wireTheHandoff } = await import("./tests/viewer.mjs");
wireTheHandoff({ has_timeline: true, trace_inline_max_bytes: inlineMax });

for (const fn of nodes.perfetto.listeners.click ?? []) await fn();
// One more turn, so a handoff that resolves late has finished.
await new Promise((resolve) => setTimeout(resolve, 30));

console.log(JSON.stringify({
  ...calls,
  status: nodes.handoff.textContent,
  fallbackHref: nodes["perfetto-link"].href,
  downloadShown: nodes["actions-download"].hidden === false,
  downloadHref: nodes["trace-download"].href,
}));
"""

INLINE_MAX = 4 * 1024 * 1024

# `UX-314`: an origin ui.perfetto.dev's own CSP will let it fetch. The
# default `bga view` port is **not** one, which is why the deep-link
# scenarios below have to say which origin they are standing on - the
# transport that wins depends on it.
FETCHABLE = "http://localhost:8080/"
REFUSED = "http://127.0.0.1:8000/"


def _click(size, inline_max=INLINE_MAX, here=FETCHABLE):
    result = subprocess.run(
        [node, "--input-type=module", "-e",
         _HARNESS % {"size": size, "inline_max": inline_max,
                     "here": json.dumps(here)}],
        capture_output=True, text=True, cwd=REPO, timeout=90)
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


@needs_node
class TestTheTransportIsChosenBySize:

    def test_a_big_trace_is_fetched_by_perfetto_not_carried(self):
        """The acceptance test's first clause. Over the threshold the
        page navigates the opened tab to the deep link, and **no byte of
        the trace is read by this page's own JS** - the only request it
        makes is the `HEAD` that told it the size.

        `UX-314`: on an origin Perfetto is allowed to fetch. This guard
        used to stand on `127.0.0.1:8000`, which Perfetto's CSP refuses,
        and asserted the navigation happened anyway - so it was green
        for the whole time the transport was broken in the field.
        """
        out = _click(size=INLINE_MAX * 3, here=FETCHABLE)
        assert out["navigated"], out
        assert out["navigated"][0].startswith("https://ui.perfetto.dev/#!/?url=")
        assert out["posted"] == 0, "the trace was posted tab to tab anyway"
        bodies = [call for call in out["fetches"] if call["method"] != "HEAD"]
        assert bodies == [], bodies
        assert "12.0 MiB" in out["status"], out["status"]
        assert "4 MiB" in out["status"], out["status"]

    def test_a_big_trace_is_not_navigated_where_perfetto_may_not_fetch(self):
        """`UX-314`, and the failure the field hit.

        Over the threshold the tab-to-tab post is refused by size and
        the deep link is refused by Perfetto's `connect-src`. The old
        code navigated anyway: ui.perfetto.dev opened, its console said
        `connect-src`, and the reader got an empty Perfetto and no
        explanation. There is no transport here, so the page must say
        that and name both ways out - not open a tab onto a refusal.
        """
        out = _click(size=INLINE_MAX * 3, here=REFUSED)
        assert out["navigated"] == [], (
            "navigated to a deep link Perfetto's CSP will refuse")
        assert out["posted"] == 0, "posted a trace over the threshold"
        assert out["closed"] >= 1, "left a blank Perfetto tab open"
        bodies = [call for call in out["fetches"] if call["method"] != "HEAD"]
        assert bodies == [], bodies
        status = out["status"]
        assert "12.0 MiB" in status, status
        assert "connect-src" in status, status
        assert "--port 8080" in status, status
        assert "drag" in status, status
        # And the route that always works is on the page.
        assert out["downloadShown"] is True, out

    def test_the_save_it_yourself_route_is_there_either_way(self):
        """Both sizes, because both transports can be refused."""
        for size in (25_000, INLINE_MAX * 3):
            out = _click(size=size, here=REFUSED)
            assert out["downloadShown"] is True, (size, out)
            assert out["downloadHref"].endswith("/timeline.json.gz"), out

    def test_a_small_trace_still_goes_tab_to_tab(self):
        """The other half, and the one `UX-198` verified: below the
        threshold nothing changes. The item is the large-size inversion
        only."""
        out = _click(size=25_000)
        assert out["posted"] == 1, out
        assert out["navigated"] == [], out
        assert [call["method"] for call in out["fetches"]] == ["HEAD", "GET"]
        assert "sent" in out["status"], out["status"]

    def test_a_server_that_does_not_say_is_treated_as_small(self):
        """An unknown size takes the transport that works today for
        every capture that fits, rather than refusing one that would
        have."""
        out = _click(size="null")
        assert out["posted"] == 1, out
        assert out["navigated"] == [], out

    def test_the_tab_is_opened_before_anything_is_awaited(self):
        """`UX-198`'s rule, which the new branch must not break: the
        click's transient activation is gone by the time an `await`
        resolves, so the window is opened first and the size asked for
        afterwards - on both paths."""
        for size in (INLINE_MAX * 3, 25_000):
            out = _click(size=size)
            assert out["opened"] == ["https://ui.perfetto.dev"], (size, out)


class TestTheThresholdIsOneNumber:

    def test_the_server_publishes_it_rather_than_the_page_repeating_it(
            self, tmp_path):
        from tools.bga_view import TRACE_BUDGET_B, serve

        run = tmp_path / "run"
        shutil.copytree(os.path.join(REPO, "tests/fixtures/golden/mixed_task_kinds"),
                        run)
        (run / "expected_output.json").unlink(missing_ok=True)
        httpd, _url = serve(str(run), port=0, with_trace=False)
        try:
            published = httpd.RequestHandlerClass.documents["run.json"]
        finally:
            httpd.server_close()
        assert published["trace_inline_max_bytes"] == TRACE_BUDGET_B

    def test_the_page_keeps_no_copy_of_it(self):
        """Two copies of one number is how they drift. The viewer may
        name the field, and may not name the value."""
        source = open(os.path.join(REPO, "bga/viewer/app.js"),
                      encoding="utf-8").read()
        assert "trace_inline_max_bytes" in source
        wired = source[source.index("export function wireTheHandoff"):]
        wired = wired[:wired.index("\n}\n")]
        assert not re.search(r"\b4\s*\*\s*1024\s*\*\s*1024\b", wired), wired
        assert str(4 * 1024 * 1024) not in wired, wired

    def test_it_is_argued_where_it_is_defined(self):
        source = open(os.path.join(REPO, "tools/bga_view.py"),
                      encoding="utf-8").read()
        head = source[:source.index("TRACE_BUDGET_B = ")]
        reason = head[head.rindex("# The trace is the one part"):]
        for word in ("postMessage", "data:", "UX-299", "4.2x"):
            assert word in reason, word


class TestTheExportSaysWhatToRunInstead:

    def test_an_over_threshold_export_carries_the_command_not_the_trace(
            self, tmp_path, monkeypatch):
        """The export half of the same threshold. A `data:` URL of
        gigabytes is not an attachment; the page says the size and names
        the command that serves it instead - the blast box's pattern."""
        import tools.bga_view as view

        run = tmp_path / "run"
        shutil.copytree(os.path.join(REPO, "tests/fixtures/golden/mixed_task_kinds"),
                        run)
        (run / "expected_output.json").unlink(missing_ok=True)
        monkeypatch.setattr(
            view, "trace_bytes",
            lambda _run: b"\x1f\x8b" + b"x" * (view.TRACE_BUDGET_B * 2))

        path = tmp_path / "report.html"
        result = view.export(str(run), str(path))
        text = path.read_text(encoding="utf-8")

        assert result["over_budget"] is False
        assert 'id="bga-trace"' not in text, "the trace was inlined anyway"
        payload = json.loads(
            re.search(r'id="bga-run">(.*?)</script>', text, re.S).group(1))
        assert payload["has_timeline"] is False
        assert "MiB" in payload["timeline_omitted"]
        recipe = payload["timeline_recipe"]
        assert recipe["command"].startswith("bga view ")
        assert recipe["command"].endswith("--perfetto")
        assert "deep link" in recipe["note"]

    def test_a_small_export_still_inlines_it(self, tmp_path):
        """Unchanged below the threshold, which is the item's own
        out-of-scope line."""
        from tools.bga_view import export

        snapshot = tmp_path / "20260821T120000Z"
        snapshot.mkdir()
        (snapshot / "build.log").write_text(
            "[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst\n"
            "[wrapper][2026-08-21 12:00:00,100] INFO: [00:00:00][aaaaaaaa][   build:work-a.bst] START Building\n"
            "[wrapper][2026-08-21 12:00:03,100] INFO: [00:00:03][aaaaaaaa][   build:work-a.bst] SUCCESS Building\n"
            "[wrapper][2026-08-21 12:00:03,200] INFO: Return code: 0\n",
            encoding="utf-8")
        shutil.copytree(os.path.join(REPO, "tests/fixtures/golden/mixed_task_kinds"),
                        snapshot / "run")
        (snapshot / "run" / "expected_output.json").unlink(missing_ok=True)
        import gzip
        with gzip.open(snapshot / "plane2.log.gz", "wt", encoding="utf-8") as handle:
            handle.write("START pid=101 ppid=1 ts=1000.000000 element=work-a.bst cmd=cc -c main.c\n"
                         "END pid=101 ppid=1 ts=1002.500000 element=work-a.bst cmd=cc -c main.c\n")

        path = tmp_path / "small.html"
        export(str(snapshot / "run"), str(path))
        text = path.read_text(encoding="utf-8")
        assert 'id="bga-trace"' in text
        payload = json.loads(
            re.search(r'id="bga-run">(.*?)</script>', text, re.S).group(1))
        assert payload["has_timeline"] is True
        assert "timeline_recipe" not in payload
