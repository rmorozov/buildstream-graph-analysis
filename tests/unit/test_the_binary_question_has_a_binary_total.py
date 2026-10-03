"""UX-1247: `by_binary` is one row per binary - CPU, wall, calls, elements - ranked by CPU.

Before: `by_binary` was `{binary: calls}` and the `binary_cost` answer sentence
summed 21,064 (element, binary) pairs in the browser to name its leader. Now
`bga.plane2.binary_totals` sums them once; the sentence and the table's first
row read `by_binary[0]`.

Styleguide §1c.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from bga.plane2 import binary_totals
from bga.report.json import _binary_rows

REPO = Path(__file__).resolve().parents[2]
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _element(*binaries):
    """One element's `binary_cost` entry with the full `binaries` list."""
    rows = [{"binary": b, "count": n, "cpu_us": cpu, "wall_s": wall} for b, n, cpu, wall in binaries]
    return {"available": True, "measured_cpu_us": sum(r["cpu_us"] for r in rows), "binaries": rows}


#: `make` has the most calls, `cc` the most CPU; `cc` ran 3 times outside any measured element.
CONSTRUCTED = {
    "by_binary": {"make": 40, "cc": 9, "sh": 12},
    "binary_cost": {
        "a.bst": _element(("make", 20, 1_000, 0.5), ("cc", 3, 4_000_000, 2.25), ("sh", 6, 2_000, 0.125)),
        "b.bst": _element(("make", 20, 1_500, 0.5), ("cc", 3, 3_000_000, 1.5)),
        "c.bst": {"available": False, "note": "no CPU time was measured for this element's processes"},
    },
}

#: A pre-`UX-1183` report: two top-N rankings, no membership list.
RANKED_ONLY = {
    "by_binary": {"make": 40, "cc": 9},
    "binary_cost": {
        "a.bst": {
            "available": True,
            "measured_cpu_us": 5_000,
            "by_cpu": [{"binary": "cc", "count": 3, "cpu_us": 4_000, "wall_s": 1.0, "cpu_share": 0.8}],
            "by_count": [{"binary": "make", "count": 20}],
        }
    },
}


def test_row_zero_is_the_cpu_leader_and_its_cpu_is_its_pairs_sum():
    rows = binary_totals(CONSTRUCTED)
    pairs = _binary_rows(CONSTRUCTED["binary_cost"])
    assert [row["binary"] for row in rows] == ["cc", "make", "sh"], rows
    for row in rows:
        mine = [pair for pair in pairs if pair["binary"] == row["binary"]]
        assert row["cpu_us"] == sum(pair["cpu_us"] for pair in mine), (row, mine)
        assert row["wall_us"] == sum(pair["wall_us"] for pair in mine), (row, mine)
        assert row["elements"] == len(mine), (row, mine)
        assert row["calls"] == CONSTRUCTED["by_binary"][row["binary"]], row


def test_a_ranked_only_report_leaves_cpu_absent_not_partial():
    rows = binary_totals(RANKED_ONLY)
    assert rows == [{"binary": "make", "calls": 40}, {"binary": "cc", "calls": 9}], rows


def test_macro_micro_publishes_the_totals_as_by_binary():
    from tools.bga_view import payloads

    run = REPO / "tests/fixtures/macro_micro/run"
    published = payloads(str(run))["report.json"]["by_binary"]
    plane2 = json.loads((REPO / "tests/fixtures/macro_micro/plane2.json").read_text(encoding="utf-8"))
    assert published == binary_totals(plane2), published[:3]
    assert len(published) == len(plane2["by_binary"]) and published[0]["binary"] == "cmake", published[:3]


_PROBE = r"""
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
const app = await import("./tests/viewer.mjs");
const { readFileSync } = await import("node:fs");
const payload = JSON.parse(readFileSync(process.env.BGA_PAYLOAD, "utf8"));
const node = JSON.parse(readFileSync(process.env.BGA_SCHEMA, "utf8")).properties.by_binary;
const find = (n, pred) => {
  if (!n) return null;
  if (pred(n)) return n;
  for (const c of n.children ?? []) { const hit = find(c, pred); if (hit) return hit; }
  return null;
};
const section = app.renderSection("by_binary", payload.by_binary, app.hintsOf(node), node, null, payload);
const first = find(section, (n) => n.tagName === "tr" && n.attrs?.["data-binary"]);
process.stdout.write(JSON.stringify({
  answer: app.SECTION_ANSWERS.binary_cost(payload.binary_cost, payload),
  first: first?.attrs?.["data-binary"] ?? null,
}));
"""


@needs_node
def test_the_answer_sentence_and_the_table_name_row_zero(tmp_path):
    from bga import schemas

    payload = {"by_binary": binary_totals(CONSTRUCTED), "binary_cost": _binary_rows(CONSTRUCTED["binary_cost"])}
    (tmp_path / "payload.json").write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "schema.json").write_text(json.dumps(schemas.schema(schemas.ANALYZE)), encoding="utf-8")
    result = subprocess.run(
        [node, "--input-type=module", "-e", _PROBE],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=120,
        env=dict(
            os.environ,
            BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs"),
            BGA_PAYLOAD=str(tmp_path / "payload.json"),
            BGA_SCHEMA=str(tmp_path / "schema.json"),
        ),
    )
    assert result.returncode == 0, result.stderr[-3000:]
    seen = json.loads(result.stdout)
    # 9 calls is the run's count from `by_binary`, not the 6 its pair rows hold.
    assert seen["answer"] == "3 binaries ran in 2 elements; cc cost the most, 9 calls, 7.0 s of CPU in 2 elements.", (
        seen
    )
    assert seen["first"] == "cc", seen
