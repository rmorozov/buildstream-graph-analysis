"""UX-725: `bga view --export` on a run mode mismatch, measured.

`bga_view.payloads()` builds its optional comparison band by running
`bga compare` in-process (`_capture`). `RunsNotComparableError` (`UX-55`,
raised when a `--baseline-run` sample's run mode differs from the
candidate's) was treated as an absence here - the report still renders -
but `_capture` never redirected stderr, so `main()`'s own two lines (a
`logger.error` record and an `Error:` print, both true of the *inner*
`bga compare` call and false of the outer `bga view --export`, which
wrote its export and exited 0) reached the real terminal anyway. The
reason was then discarded, so the page had nothing to say about the
missing band either.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _run_mode_store(tmp_path, candidate_mode, baseline_mode):
    """A two-run store whose runs differ in run mode - `UX-55`'s
    `RunsNotComparableError` shape, not `MIN_BASELINE_RUNS`' shortfall
    one (`test_the_views_nobody_could_reach.py` already covers that)."""
    (tmp_path / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    with open(os.path.join(GOLDEN, "run-context.json")) as handle:
        base_context = json.load(handle)

    def _write(stamp, mode):
        run = tmp_path / ".bga" / "runs" / stamp / "run"
        run.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        context = dict(base_context, queue_summary={
            "build": ({"processed": 5, "skipped": 0} if mode == "full"
                      else {"processed": 1, "skipped": 4})})
        (run / "run-context.json").write_text(json.dumps(context))
        return str(run)

    _write("20260101T000000Z", baseline_mode)
    return _write("20260102T000000Z", candidate_mode)


def _run_json_block(html, name):
    match = re.search(
        r'<script type="application/json" id="bga-' + re.escape(name)
        + r'">([\s\S]*?)</script>', html)
    return json.loads(match.group(1)) if match else None


def test_the_export_exits_clean_with_no_error_line(tmp_path, capsys):
    """The Acceptance Test's first two clauses: exit 0, no `^ERROR|^Error:`.

    Mutation: restore the stderr pair (drop `redirect_stderr` in
    `_capture`) and this reds on both the duplicate and the word - see
    `test_the_reason_appears_exactly_once` for the duplicate half.
    """
    from tools import bga_view

    run = _run_mode_store(tmp_path, candidate_mode="full", baseline_mode="incremental")
    page = tmp_path / "out.html"

    code = bga_view.main([run, "--export", str(page)])

    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert page.exists() and page.stat().st_size > 0
    assert not re.search(r"^ERROR|^Error:", captured.err, re.M), captured.err


def test_the_reason_appears_exactly_once(tmp_path, capsys):
    """The duplicate half: the UX-55 sentence must not print twice (once
    logged, once as `Error:`) even off the visible error markers above -
    a mutation that kept the words but dropped only the prefixes would
    pass the clause above and must not pass this one."""
    from tools import bga_view

    run = _run_mode_store(tmp_path, candidate_mode="full", baseline_mode="incremental")
    page = tmp_path / "out.html"

    bga_view.main([run, "--export", str(page)])

    captured = capsys.readouterr()
    occurrences = captured.err.count("noise band may only be built")
    assert occurrences == 0, (
        f"the refusal sentence reached the real terminal {occurrences} "
        f"time(s): {captured.err!r}")


def test_the_page_carries_the_bands_reason(tmp_path):
    """`UX-388`'s absence vocabulary, on the surface the export carries:
    the `run` document names why the band is missing instead of the
    page simply having no band and no explanation."""
    from tools import bga_view

    run = _run_mode_store(tmp_path, candidate_mode="full", baseline_mode="incremental")
    page = tmp_path / "out.html"

    bga_view.export(run, str(page))
    run_doc = _run_json_block(page.read_text(encoding="utf-8"), "run")

    assert run_doc is not None
    reason = run_doc.get("comparison_unavailable")
    assert reason, "the export has nothing to say about the missing band"
    assert "incremental run" in reason and "candidate is full" in reason, reason
    assert "UX-55" in reason, reason


def test_a_comparable_pair_carries_no_such_note(tmp_path):
    """The other direction: a store with no run-mode mismatch must not
    grow this key - it is not a general "no band" caption."""
    from tools import bga_view

    (tmp_path / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    stamps = ["20260101T000000Z", "20260102T000000Z"]
    for stamp in stamps:
        run = tmp_path / ".bga" / "runs" / stamp / "run"
        run.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
    page = tmp_path / "out.html"

    bga_view.export(str(tmp_path / ".bga" / "runs" / stamps[-1] / "run"), str(page))
    run_doc = _run_json_block(page.read_text(encoding="utf-8"), "run")

    assert "comparison_unavailable" not in run_doc


@needs_node
def test_render_band_unavailable_writes_the_empty_section_vocabulary():
    """The rendering half, isolated: given the reason `payloads()` now
    carries, `renderBandUnavailable` draws exactly what `UX-388` draws
    for any other empty population - a heading, one line, `data-empty`."""
    script = _HARNESS % json.dumps(
        "baseline run x is a full run but the candidate is incremental "
        "- a noise band may only be built from runs of the same kind "
        "(UX-55)")
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True,
                            cwd=os.getcwd(), timeout=60)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out["section"] == "band"
    assert out["empty"] == "true"
    assert "No comparison band" in out["text"]
    assert "full run" in out["text"] and "incremental" in out["text"]


_HARNESS = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument({
  createElement: (t) => _makeNode(t), createElementNS: (_n, t) => _makeNode(t),
  getElementById: () => _makeNode("div"),
});
const mod = await import("./tests/viewer.mjs");
const node = mod.renderBandUnavailable(%s);
console.log(JSON.stringify({
  section: node.attrs["data-section"], empty: node.attrs["data-empty"],
  text: node.children.map((c) => c.textContent ?? "").join(" "),
}));
"""
