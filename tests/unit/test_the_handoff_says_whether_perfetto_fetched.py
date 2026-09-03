"""UX-521: the deep-link handoff, and the two waits it could not tell apart.

Over `TRACE_BUDGET_B` the page hands Perfetto a URL and returns
(`UX-299`). There is no callback on that path and no `postMessage`, so
the report tab's last word is a sentence written at t=0 - and it is the
*same* sentence whether Perfetto is fetching gigabytes and parsing them,
or never asked at all. Two waits that want opposite actions from the
reader, rendered identically for minutes. The field report is that wait.

The server has the fact the page is missing: the trace is served from
this process, so it sees Perfetto's `GET` arrive. `trace-status.json`
is that fact and nothing more - a count and a size, never a percentage,
because what happens after the bytes land is Perfetto's parse.

The discriminating case is the `HEAD`. The page measures the trace with
one before it picks a transport, so a counter that counted requests
rather than *bodies* would report "Perfetto has the whole trace" at the
moment zero bytes had been sent, which is the failure this item exists
to remove wearing a new hat.
"""
import gzip
import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

import pytest

REPO = str(pathlib.Path(__file__).resolve().parents[2])
sys.path.insert(0, REPO)

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"

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
    snap = tmp_path / "20260821T120000Z"
    snap.mkdir()
    (snap / "build.log").write_text(_WRAPPED)
    shutil.copytree(os.path.join(REPO, GOLDEN), snap / "run")
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


def _status(url):
    from tools.bga_view import TRACE_STATUS_NAME

    with urllib.request.urlopen(url + TRACE_STATUS_NAME, timeout=15) as answer:
        return json.loads(answer.read())


def _fetch_trace(url, method="GET"):
    from tools.bga_view import TRACE_NAME

    request = urllib.request.Request(url + TRACE_NAME, method=method)
    with urllib.request.urlopen(request, timeout=30) as answer:
        return len(answer.read())


def _status_when(url, fetches, within=10.0):
    """`trace-status.json`, once the server has recorded `fetches`.

    `UX-546`. `_trace` increments the counter in the request thread
    **after** the body has left the socket, so "the client holds the
    bytes" and "the count moved" are two events with nothing ordering
    them. A 4-core box, one fetch then an immediate status ask, x600:

    ```text
    loadavg   first read stale   the count arrived
      0.09      0 of 600         -
      7.12      3 of 600         4.2, 5.5, 5.9 ms late
    ```

    So this waits on the **condition**, not on a duration, and returns
    the last reading either way - a count that never arrives is still
    the wrong dict, and still reddens the caller's assertion.
    """
    deadline = time.monotonic() + within
    while True:
        seen = _status(url)
        if seen["fetches"] >= fetches or time.monotonic() > deadline:
            return seen


class TestTheServerKnowsWhetherTheTraceWasFetched:
    def test_before_anyone_asks_it_says_nothing_has(self, snapshot, served):
        """The state the page starts in, and the one it must not
        mistake for success: a server that reported a fetch before
        serving one would print "Perfetto has it" over a blank tab."""
        assert _status(served(snapshot / "run")) == {"fetches": 0, "bytes": 0}

    def test_a_served_body_is_a_fetch_and_carries_its_size(
            self, snapshot, served):
        """`UX-546`: read through `_status_when`, which is where the
        3-in-600-at-loadavg-7.12 race and its 4.2-5.9 ms are measured.
        """
        url = served(snapshot / "run")
        sent = _fetch_trace(url)
        assert _status_when(url, 1) == {"fetches": 1, "bytes": sent}

    def test_a_head_is_not_a_fetch(self, snapshot, served):
        """The page's own transport decision (`UX-299`) is a `HEAD`, so
        every deep link is preceded by one. Counting it would make the
        answer true before a single trace byte had been written."""
        url = served(snapshot / "run")
        assert _fetch_trace(url, method="HEAD") == 0
        assert _status(url) == {"fetches": 0, "bytes": 0}

    def test_a_second_reader_is_a_second_fetch(self, snapshot, served):
        """Population *many*: two tabs on one server. The count rises,
        the size does not - it is the trace's size, not a total.

        `UX-546`: two fetches are two chances to read the count before
        the request thread has written it, at the rate `_status_when`
        measures (3 of 600 at loadavg 7.12, 0 of 600 at 0.09).
        """
        url = served(snapshot / "run")
        sent = _fetch_trace(url)
        _fetch_trace(url)
        assert _status_when(url, 2) == {"fetches": 2, "bytes": sent}

    def test_two_servers_do_not_share_the_answer(self, snapshot, served):
        """`_Handler` carries this on the class `serve` builds per run,
        so a second `bga view` in the same process starts at zero.

        `UX-546`: the second server is read *after* the first has
        settled, so the zero is a server that was never asked rather
        than one whose request thread has not run yet - the ordering
        the 4.2-5.9 ms in `_status_when` is measured against, at
        loadavg 7.12.
        """
        first, second = served(snapshot / "run"), served(snapshot / "run")
        _fetch_trace(first)
        assert _status_when(first, 1)["fetches"] == 1
        assert _status(second)["fetches"] == 0

    def test_the_two_route_constants_agree(self):
        """One name is in Python and one in JavaScript, the way
        `PERFETTO_ORIGIN` is. Nothing else would notice them drifting:
        the page would fetch a 404, swallow it as "the server is gone",
        and go quietly back to the single sentence this item removed."""
        from tools.bga_view import TRACE_STATUS_NAME

        source = open(os.path.join(REPO, "bga/viewer/app.js")).read()
        declared = source.split('TRACE_STATUS_URL = "')[1].split('"')[0]
        assert declared == TRACE_STATUS_NAME

    def test_it_declares_no_schema(self, snapshot, served):
        """Deliberate, and the reason is written in `_trace_status`: a
        liveness fact - true for one second of one server's life - has
        no business in the registry beside documents a reader keeps,
        cites and diffs. The guard is here so it stays a decision."""
        assert "schema" not in _status(served(snapshot / "run"))


# The page side. `wireTheHandoff` runs for real under Node against the
# DOM double `UX-299`'s guard established; what is new is a clock the
# test drives, so five minutes of polling costs no wall time.
_HARNESS = """
const size = %(size)s;
const inlineMax = %(inline_max)s;
const here = %(here)s;
const answers = %(answers)s;

const calls = { statusAsks: 0, delays: [], said: [] };
const realTimeout = globalThis.setTimeout;

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
const handoff = nodes.handoff;
Object.defineProperty(handoff, "textContent", {
  get() { return calls.said.at(-1) ?? ""; },
  set(value) { calls.said.push(String(value)); },
});

globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument({ getElementById: (id) => nodes[id] ?? null });
globalThis.location = { href: here + "index.html" };

globalThis.fetch = async (url, init = {}) => {
  const method = init.method ?? "GET";
  if (String(url).includes("trace-status.json")) {
    const at = calls.statusAsks++;
    const answer = answers[Math.min(at, answers.length - 1)];
    // The one input class a status endpoint really has besides its two
    // answers: no answer at all, because `bga view` was stopped while
    // Perfetto loads.
    if (answer === "gone") throw new Error("connection refused");
    return { ok: true, json: async () => answer };
  }
  if (method === "HEAD") {
    return { ok: true, headers: { get: (k) =>
      k.toLowerCase() === "content-length" ? String(size) : null } };
  }
  return {
    ok: true,
    headers: { get: () => null },
    arrayBuffer: async () => new Uint8Array([1, 2, 3, 4, 5]).buffer,
  };
};

// A clock the test turns. Every scheduled callback runs immediately on
// the microtask queue, and its requested delay is recorded - so the
// ceiling is reached in milliseconds and the interval is still asserted.
const pending = [];
globalThis.setTimeout = (fn, ms) => {
  calls.delays.push(ms);
  pending.push(fn);
  return 0;
};

const tab = {
  set location(value) { calls.navigated = String(value); },
  postMessage(message) {
    if (message === "PING") {
      (globalThis.__listeners ?? []).forEach(
        (fn) => fn({ origin: "https://ui.perfetto.dev", data: "PONG" }));
      return;
    }
    calls.posted = (calls.posted ?? 0) + 1;
  },
  close() { calls.closed = (calls.closed ?? 0) + 1; },
};
globalThis.__listeners = [];
globalThis.window = {
  open(url) { return tab; },
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
// Turn the clock until nothing more is scheduled, or far past the
// ceiling - an unbounded poll must fail loudly rather than hang.
let turns = 0;
while (pending.length && turns++ < 5000) {
  await pending.shift()();
  await new Promise((resolve) => realTimeout(resolve, 0));
}
calls.turns = turns;

console.log(JSON.stringify(calls));
"""

INLINE_MAX = 4 * 1024 * 1024
FETCHABLE = "http://localhost:8080/"
REFUSED = "http://127.0.0.1:8000/"
NOT_YET = [{"fetches": 0, "bytes": 0}]
LANDED = [{"fetches": 0, "bytes": 0}, {"fetches": 1, "bytes": 9_000_000}]


def _click(answers, size=9_000_000, inline_max=INLINE_MAX, here=FETCHABLE):
    result = subprocess.run(
        [node, "--input-type=module", "-e",
         _HARNESS % {"size": size, "inline_max": inline_max,
                     "here": json.dumps(here),
                     "answers": json.dumps(answers)}],
        capture_output=True, text=True, cwd=REPO, timeout=90)
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


@needs_node
class TestOnlyTheDeepLinkPathAsks:
    def test_the_over_threshold_handoff_asks(self):
        assert _click(NOT_YET)["statusAsks"] > 0

    def test_the_copied_trace_never_asks(self):
        """Under the threshold the page carries the bytes itself and
        the `postMessage` handshake already answers (`UX-198`). Asking
        the server would be a poll with nothing to learn."""
        assert _click(NOT_YET, size=1024)["statusAsks"] == 0

    def test_a_refused_origin_never_asks(self):
        """`UX-314` closes the tab and says why. There is no fetch to
        wait for, and a page still asking would contradict its own
        sentence every two seconds."""
        assert _click(NOT_YET, here=REFUSED)["statusAsks"] == 0


def _after_the_handoff(result):
    """What the rail said once the transport was chosen.

    The click's own first line - "opening ui.perfetto.dev" - is written
    before the `HEAD` comes back, so it belongs to neither transport
    and is dropped here rather than counted as one of this item's
    sentences.
    """
    said = result["said"]
    assert said[0].startswith("opening ui.perfetto.dev"), said
    return said[1:]


@needs_node
class TestTheSentenceChangesWhenTheFetchLands:
    def test_at_t0_it_says_the_tab_stays_blank(self):
        first = _after_the_handoff(_click(NOT_YET))[0]
        assert "MiB" in first and "blank" in first

    def test_a_fetch_that_never_lands_leaves_one_sentence(self):
        """The pre-item behaviour, now the *honest* half of a pair: if
        Perfetto never asked, the page must not claim it did."""
        said = _after_the_handoff(_click(NOT_YET))
        assert len(said) == 1, said

    def test_a_landed_fetch_gets_its_own_sentence(self):
        said = _after_the_handoff(_click(LANDED))
        assert len(said) == 2, said
        assert "fetched" in said[1] and "parsing" in said[1]
        assert said[1] != said[0]

    def test_it_stops_asking_once_it_knows(self):
        """`UX-334`: the answer changes at most once, so a poll running
        after it arrived is a leak with no question left to ask."""
        landed = _click(LANDED)
        assert landed["statusAsks"] == 2, landed["statusAsks"]

    def test_it_promises_no_share_of_perfettos_parse(self):
        """Out of Scope, made a guard: this repository does not control
        Perfetto's parse and must not print a fraction of it."""
        said = _after_the_handoff(_click(LANDED))[1]
        assert "%" not in said


@needs_node
class TestTheAskingIsBounded:
    def test_it_asks_at_the_published_interval(self):
        source = open(os.path.join(REPO, "bga/viewer/app.js")).read()
        every = int(source.split("FETCH_POLL_MS = ")[1].split(";")[0])
        assert set(_click(NOT_YET)["delays"]) == {every}

    def test_it_gives_up_at_the_published_ceiling(self):
        """A wait nobody ends is the console `UX-334` cleaned. The
        loop above turns the clock 5000 times; the count proves the
        stop is the constant and not the test running out of patience."""
        source = open(os.path.join(REPO, "bga/viewer/app.js")).read()
        limit = int(source.split("FETCH_POLL_LIMIT = ")[1].split(";")[0])
        assert _click(NOT_YET)["statusAsks"] == limit

    def test_a_server_that_stops_answering_ends_the_watch(self):
        """Input class *error*: `bga view` was Ctrl-C'd while Perfetto
        loads. The sentence on screen is still true; a page retrying a
        dead socket for five minutes is not an improvement on it."""
        assert _click(["gone"])["statusAsks"] == 1
