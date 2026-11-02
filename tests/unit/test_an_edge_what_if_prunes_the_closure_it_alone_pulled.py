"""UX-1357: `bga whatif --drop-edge` replays without the edge and prunes what only it pulled in.

The fixture is fdsdk's libxml2 -> doxygen shape at toy scale: `app.bst`
build-depends on `doc.bst`, which alone pulls a 30 s chain and a 40 s
runtime-only dependency onto the build. Zeroing `doc.bst` leaves the
chain; dropping the edge removes it.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

S = 1_000_000
BUILD = {
    "base.bst": 2,
    "lib.bst": 2,
    "h1.bst": 10,
    "h2.bst": 10,
    "h3.bst": 10,
    "doc.bst": 3,
    "rt.bst": 40,
    "app.bst": 1,
}
EDGES = [
    ("base.bst", "lib.bst", "build"),
    ("lib.bst", "app.bst", "build"),
    ("h1.bst", "h2.bst", "build"),
    ("h2.bst", "h3.bst", "build"),
    ("h3.bst", "doc.bst", "build"),
    ("rt.bst", "doc.bst", "runtime"),
    ("doc.bst", "app.bst", "build"),
]
DOC_EDGE = ("doc.bst", "app.bst")

JUNCTION = {"a.bst:b.bst": 5, "c.bst": 5, "a.bst": 5, "b.bst:c.bst": 5, "t.bst": 1}
JUNCTION_EDGES = [
    ("a.bst:b.bst", "c.bst", "build"),
    ("a.bst", "b.bst:c.bst", "build"),
    ("c.bst", "t.bst", "build"),
    ("b.bst:c.bst", "t.bst", "build"),
]
TWO_TARGETS = {"s.bst": 4, "u.bst": 4, "x.bst": 4, "t1.bst": 1, "t2.bst": 1}
TWO_TARGET_EDGES = [
    ("s.bst", "x.bst", "build"),
    ("u.bst", "x.bst", "build"),
    ("x.bst", "t1.bst", "build"),
    ("s.bst", "t2.bst", "build"),
]


def _write_run(root, build=BUILD, edges=EDGES, targets=("app.bst",), starts=None):
    run = root / "run"
    run.mkdir()
    elements = [{"uid": uid, "cache_key": None, "requested_target": uid in targets} for uid in build]
    deps = [{"predecessor": p, "successor": s, "dependency_type": t} for p, s, t in edges]
    (run / "graph.json").write_text(json.dumps({"elements": elements, "dependencies": deps}))
    if starts is None:
        starts = {"base.bst": 0, "lib.bst": 2, "h1.bst": 0, "rt.bst": 0, "h2.bst": 10, "h3.bst": 20, "doc.bst": 30}
        starts["app.bst"] = 40
    spans = [
        {
            "task_key": f"{uid}|BUILD|BUILD|0",
            "ts_us": starts[uid] * S,
            "dur_us": build[uid] * S,
            "resources": ["PROCESS"],
            "primary_resource": "PROCESS",
        }
        for uid in build
    ]
    (run / "trace.json").write_text(json.dumps({"spans": spans}))
    context = {
        "trace_epsilon_us": 1000,
        "wall_clock": {"start_us": 0, "end_us": 41 * S},
        "max_jobs": 3,
        "resource_capacities": {"PROCESS": 3},
    }
    (run / "run-context.json").write_text(json.dumps(context))
    return run


def _whatif(run, *args):
    out = subprocess.run(
        [sys.executable, "-c", "from bga.cli import main; raise SystemExit(main())", "whatif", str(run), *args],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )
    assert out.returncode == 0, out.stderr
    return out.stdout


@pytest.fixture
def run(tmp_path):
    return _write_run(tmp_path)


def test_dropping_the_edge_prunes_the_chain_it_alone_pulled(run):
    edges = json.loads(_whatif(run, "--drop-edge", *DOC_EDGE, "--format", "json"))["edges"]
    projected = edges["projected"]
    assert edges["refusals"] == []
    assert projected["pruned"] == ["doc.bst", "h1.bst", "h2.bst", "h3.bst", "rt.bst"]
    assert (projected["elements_before"], projected["elements_after"]) == (8, 3)
    assert projected["baseline_makespan_us"] == 41 * S
    assert projected["makespan_after_us"] == 5 * S


def test_a_runtime_only_dep_of_a_build_dep_gates_the_build(run):
    """`rt.bst` (40 s) gates `app.bst` through `doc.bst`: 41 s with it, 34 s once only `rt -> doc` is dropped."""
    projected = json.loads(_whatif(run, "--drop-edge", "rt.bst", "doc.bst", "--format", "json"))["edges"]["projected"]
    assert projected["pruned"] == ["rt.bst"]
    assert (projected["baseline_makespan_us"], projected["makespan_after_us"]) == (41 * S, 34 * S)


def test_an_edge_not_in_the_graph_is_refused_with_the_nearest_names(run):
    document = json.loads(_whatif(run, "--drop-edge", "doc.bst", "ap.bst", "--format", "json"))
    (refusal,) = document["edges"]["refusals"]
    assert refusal["check"] == "unknown_edge"
    assert "app.bst" in refusal["sentence"]
    assert document["edges"]["projected"] is None and document["refusals"] == []


def test_the_text_says_it_is_a_priced_question(run):
    text = _whatif(run, "--drop-edge", *DOC_EDGE)
    assert "Replayed makespan: 41.0 s -> 5.0 s" in text
    assert "8 -> 3; pruned 5: doc.bst, h1.bst, h2.bst, h3.bst, rt.bst" in text
    assert "not a removal verdict" in text


def test_the_served_answer_is_the_cli_answer(run):
    import tools.bga_view as view

    cli = _whatif(run, "--drop-edge", *DOC_EDGE, "--format", "json")
    assert json.dumps(view.whatif_answer(str(run), [], [list(DOC_EDGE)]), indent=2, default=str) == cli.strip()


def _junction_run(tmp_path):
    starts = {"a.bst:b.bst": 0, "a.bst": 0, "c.bst": 5, "b.bst:c.bst": 5, "t.bst": 10}
    return _write_run(tmp_path, JUNCTION, JUNCTION_EDGES, ("t.bst",), starts)


@pytest.mark.parametrize(
    ("pair", "pruned"),
    [
        (("a.bst:b.bst", "c.bst"), ["a.bst:b.bst"]),
        (("a.bst", "b.bst:c.bst"), ["a.bst"]),
    ],
)
def test_a_junction_qualified_endpoint_is_named_by_two_arguments(tmp_path, pair, pruned):
    """`a.bst:b.bst:c.bst` is two different edges here; the pair never guesses which."""
    edges = json.loads(_whatif(_junction_run(tmp_path), "--drop-edge", *pair, "--format", "json"))["edges"]
    assert edges["refusals"] == [] and edges["dropped"] == [list(pair)]
    assert edges["projected"]["pruned"] == pruned


def test_the_server_carries_a_junction_pair_as_the_cli_does(tmp_path):
    import threading
    import urllib.parse
    import urllib.request

    from tools.bga_view import serve

    run = _junction_run(tmp_path)
    httpd, url = serve(str(run))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        for pair in (["a.bst:b.bst", "c.bst"], ["a.bst", "b.bst:c.bst"]):
            query = "&".join(f"drop_edge={urllib.parse.quote(name, safe='')}" for name in pair)
            served = json.loads(urllib.request.urlopen(f"{url}whatif.json?{query}").read())
            printed = json.loads(_whatif(run, "--drop-edge", *pair, "--format", "json"))
            assert served == printed and served["edges"]["dropped"] == [pair]
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(f"{url}whatif.json?drop_edge=a.bst:b.bst:c.bst")
        assert caught.value.code == 400
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_every_requested_target_keeps_what_it_still_needs(tmp_path):
    """`t1` alone needed `x` and `u`; `t2` still needs `s`, so `s` is not pruned."""
    starts = {"s.bst": 0, "u.bst": 0, "x.bst": 4, "t1.bst": 8, "t2.bst": 4}
    run = _write_run(tmp_path, TWO_TARGETS, TWO_TARGET_EDGES, ("t1.bst", "t2.bst"), starts)
    projected = json.loads(_whatif(run, "--drop-edge", "x.bst", "t1.bst", "--format", "json"))["edges"]["projected"]
    assert projected["pruned"] == ["u.bst", "x.bst"]
    assert (projected["elements_before"], projected["elements_after"]) == (5, 3)


node = shutil.which("node")

_HARNESS = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
const views = await import("./tests/viewer.mjs");
const asked = [];
const ask = __SERVED__ ? (edge) => { asked.push(edge); return Promise.resolve(__ANSWER__); } : null;
const block = views.renderEdgeWhatIf(__PAYLOAD__, ask, { run: "RUN" });
const find = (role) => { let hit = null;
  (function walk(m) { if (!m || hit) return; if (m.attrs?.["data-role"] === role) { hit = m; return; }
    (m.children ?? []).forEach(walk); })(block); return hit; };
const text = (n) => n.textContent ?? "";
const button = (function walk(m) { if (!m) return null; if (m.tagName === "button") return m;
  for (const c of m.children ?? []) { const h = walk(c); if (h) return h; } return null; })(block);
(button.listeners.click ?? []).forEach((f) => f());
await new Promise((r) => setTimeout(r, 0));
const answer = find("edge-whatif-answer");
console.log(JSON.stringify({ asked, source: answer.attrs["data-source"], answer: text(answer), live: answer.attrs["aria-live"],
  pruned: text(find("edge-whatif-pruned")), edge: find("edge-whatif-edge").value }));
"""


@pytest.mark.skipif(node is None, reason="node is not installed")
@pytest.mark.parametrize("served", [True, False])
def test_the_chain_card_prices_a_chain_edge(run, served):
    chain = [{"element_uid": uid} for uid in ("h3.bst", "doc.bst", "app.bst")]
    payload = {"critical_path_detail": chain, "total_duration_us": 41 * S}
    answer = json.loads(_whatif(run, "--drop-edge", *DOC_EDGE, "--format", "json"))
    script = (
        _HARNESS.replace("__PAYLOAD__", json.dumps(payload))
        .replace("__SERVED__", "true" if served else "false")
        .replace("__ANSWER__", json.dumps(answer))
    )
    out = subprocess.run([node, "--input-type=module", "-e", script], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    state = json.loads(out.stdout)
    assert state["edge"] == "1"
    if served:
        assert state["asked"] == [list(DOC_EDGE)] and state["source"] == "server"
        assert "41.0 s → 5.0 s" in state["answer"] and "8 → 3 elements" in state["answer"]
        assert "not a removal verdict" in state["answer"]
        # A printout drops the select, so the answer names the edge; a reader hears it (aria-live).
        assert state["answer"].startswith("Without doc.bst → app.bst ") and state["live"] == "polite"
        assert state["pruned"] == "Pruned 5 elements: doc.bst, h1.bst, h2.bst, h3.bst, rt.bst."
    else:
        assert state["source"] == "command" and state["answer"] == "bga whatif RUN --drop-edge doc.bst app.bst"
