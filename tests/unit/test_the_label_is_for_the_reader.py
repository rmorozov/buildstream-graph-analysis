"""UX-351: a label does not print the unit its value already carries.

`title(key)` turned a payload key into a label by replacing
underscores with spaces. `UX-341` made every duration key end `_us`
and every memory key end `_bytes` - right for the contract, and it put
this on the page:

```text
Execution on chain us    43.2 s   Time the chain's own elements spent...
Dependency wait us        0 ms    Time a chain element spent ready but...
Idle us                   0 ms    Time with nothing running at all.
```

"Execution on chain us" is not English, and the `us` is answering a
question the number beside it has already answered. Measured on the
exported report when this was filed: **12 such labels on golden, 16 on
`macro_micro`**.

The rule is keyed by the *quantity*, not by the suffix: `_us` comes
off a `duration_us` and stays on anything else. `TestTheRuleIsTheDecl`
below is the half that holds that distinction - a key spelled like a
duration and declared a `count` keeps every token it has, because
there the suffix is telling the reader something true and surprising.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

FIXTURES = {"golden": REPO / "tests/fixtures/golden/mixed_task_kinds",
            "macro_micro": REPO / "tests/fixtures/macro_micro/run"}
chrome = find_chrome()
node = shutil.which("node")
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: The trailing token each quantity accounts for, as the reader would
#: read it - the label spelling of `format.js`'s `UNIT_SUFFIX`, which
#: is the table under test. Only the quantities whose *rendered value*
#: spells its unit: a `count` renders as a bare number, so "Process
#: count" is telling a reader something `1,204` does not.
UNIT_TOKEN = {
    "duration_us": "us",
    "seconds": "seconds",
    "bytes": "bytes",
    "megabytes": "mb",
    "kilobytes": "kb",
    "share": "share",
    "percent": "pct",
}

_LABELS = """
(() => {
  // `UX-347`'s chapters fold. Open them: this is a claim about every
  // label in the document, not about the ones drawn right now.
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  // The `<dt>` carries `UX-317`'s `?` marker inside it, so the label is
  // the term's own text - otherwise "Category us?" reads as ending in
  // a question mark and slips past every check below.
  const own = (node) => [...node.childNodes]
    .filter((n) => n.nodeType === 3)
    .map((n) => n.textContent).join("").trim();
  const numeric = (node) => {
    if (!node) return false;
    if (node.querySelector?.(".num")) return true;
    const raw = node.getAttribute?.("data-raw");
    return raw !== null && raw !== undefined && raw !== ""
      && Number.isFinite(Number(raw));
  };
  const out = [];
  for (const node of document.querySelectorAll("dt[data-key]")) {
    out.push({ key: node.getAttribute("data-key"), label: own(node),
               // A term whose value is a sentence carries no unit for
               // the label to repeat; one whose value is a number does.
               numeric: numeric(node.nextElementSibling) });
  }
  for (const node of document.querySelectorAll("th[data-column]")) {
    const column = node.getAttribute("data-column");
    const cell = node.closest("table")?.querySelector(
      `td[data-column="${CSS.escape(column)}"]`);
    out.push({ key: column, label: own(node), numeric: numeric(cell) });
  }
  return out;
})()
"""

#: Every *declared* quantity in the payload, by the key it is declared
#: on - both channels, resolved through the page's own helpers, which
#: is the same walk `UX-343`'s and `UX-345`'s censuses make. A name can
#: legitimately be declared more than once (`total_duration_us` sits at
#: six paths), so this collects a set per name.
_CENSUS = r"""
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null, querySelector: () => null,
                        querySelectorAll: () => [], addEventListener: () => {} };
const v = await import(process.env.BGA_VIEWER);
const fs = await import("node:fs");
const payload = JSON.parse(fs.readFileSync(process.env.BGA_PAYLOAD, "utf8"));
const schemas = JSON.parse(fs.readFileSync(process.env.BGA_SCHEMAS, "utf8"));

const found = {};
const note = (key, quantity) => {
  if (!quantity) return;
  (found[key] ??= []).includes(quantity) || found[key].push(quantity);
};
function columnsOf(node) {
  const out = new Map();
  for (const spec of v.hintsOf(node)["bga:columns"] ?? []) {
    if (spec && typeof spec === "object" && spec.key) {
      out.set(spec.key, spec.quantity);
      note(spec.key, spec.quantity);
    }
  }
  return out;
}
function walk(value, node, path, columns) {
  note(path[path.length - 1], v.hintsOf(node)["bga:quantity"]);
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const here = columnsOf(node);
    for (const [k, sub] of Object.entries(value)) {
      walk(sub, v.childNode(node, k), path.concat(k), here.size ? here : columns);
    }
  } else if (Array.isArray(value)) {
    const here = columnsOf(node);
    const items = v.childNode(node, "__item__");
    for (const sub of value) {
      walk(sub, items, path.concat("[]"), here.size ? here : columns);
    }
  } else if (typeof value === "number" && Number.isFinite(value)) {
    const key = path[path.length - 1];
    note(key, columns && columns.get(key));
  }
}
walk(payload, schemas[payload.schema], [], null);
console.log(JSON.stringify(found));
"""

#: `title()` alone, over the cases the rule is a rule about.
_TITLES = r"""
const v = await import(process.env.BGA_VIEWER);
const cases = JSON.parse(process.env.BGA_CASES);
console.log(JSON.stringify(cases.map(([key, kind]) => v.title(key, kind))));
"""


def _run(script, env):
    done = subprocess.run(
        [node, "--input-type=module", "-e", script],
        capture_output=True, text=True, cwd=REPO, timeout=120,
        env={**os.environ,
             "BGA_DOM_SHIM": (REPO / "tests/dom_shim.mjs").as_uri(),
             "BGA_VIEWER": (REPO / "tests/viewer.mjs").as_uri(), **env})
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


def _declared(label):
    """`{key: [quantity, ...]}` for every declaration in the payload."""
    from bga import schemas
    from tools.bga_view import payloads

    scratch = pathlib.Path(tempfile.mkdtemp())
    (scratch / "payload.json").write_text(
        json.dumps(payloads(str(FIXTURES[label]))["report.json"]))
    (scratch / "schemas.json").write_text(
        json.dumps({name: schemas.schema(name) for name in schemas.names()}))
    return _run(_CENSUS, {"BGA_PAYLOAD": str(scratch / "payload.json"),
                          "BGA_SCHEMAS": str(scratch / "schemas.json")})


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    import tools.bga_view as view

    made = {}
    for name, fixture in FIXTURES.items():
        run = tmp_path_factory.mktemp(f"label-{name}") / "run"
        shutil.copytree(fixture, run)
        (run / "expected_output.json").unlink(missing_ok=True)
        page = tmp_path_factory.mktemp(f"label-page-{name}") / "report.html"
        view.export(str(run), str(page))
        made[name] = page.as_uri()
    return made


@needs_browser
@needs_node
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestNoLabelPrintsWhatItsValueCarries:
    def test_no_rendered_label_ends_in_a_unit_its_quantity_carries(
            self, browser, pages, label):
        """The acceptance, on the shape a reader is handed. Every
        rendered term and column header, against what the payload
        declares that key to be."""
        declared = _declared(label)
        drawn = browser.measure(pages[label], _LABELS, 1440, 900)
        assert drawn, f"{label}: the page draws no labelled terms at all"
        bad = []
        for item in drawn:
            # The population the acceptance names: a term whose *value*
            # carries the unit. A key drawn beside a sentence -
            # `attribution_hints` is eight of them, keyed by the metric
            # each sentence explains - repeats nothing, because the
            # sentence spells no unit for the label to duplicate.
            if not item["numeric"]:
                continue
            for quantity in declared.get(item["key"], []):
                token = UNIT_TOKEN.get(quantity)
                if token and item["label"].lower().endswith(f" {token}"):
                    bad.append((item["label"], item["key"], quantity))
        assert bad == [], (
            f"{label}: {len(bad)} label(s) print a unit their declared "
            f"quantity already carries: {sorted(set(bad))[:8]}")

    def test_the_labels_are_still_labels(self, browser, pages, label):
        """The other direction. Trimming a token off a key must not
        leave an empty `<dt>`, and the population has to stay the size
        it was - a rule that silently dropped terms would pass the
        clause above perfectly."""
        drawn = browser.measure(pages[label], _LABELS, 1440, 900)
        empty = [item for item in drawn if not item["label"]]
        assert empty == [], f"{label}: {len(empty)} label(s) render empty"
        assert len(drawn) >= 200, (
            f"{label}: only {len(drawn)} labelled terms on the page")


@needs_node
class TestTheRuleIsTheDeclaration:
    """Not a list of suffixes. The distinction is the whole item: a key
    named like a duration and declared as something else keeps its
    suffix, because there it is the surprising and true half of the
    label."""

    def test_the_suffix_comes_off_the_quantity_that_accounts_for_it(self):
        cases = [["execution_on_chain_us", "duration_us"],
                 ["peak_rss_bytes", "bytes"],
                 ["useful_share", "share"]]
        assert _run(_TITLES, {"BGA_CASES": json.dumps(cases)}) == [
            "Execution on chain", "Peak rss", "Useful"]

    def test_a_key_that_only_looks_like_a_duration_keeps_its_suffix(self):
        """`_us` on a `count` is not a unit the value spells - the
        number renders as `1204`, and a label reading "Retries" where
        the key is `retries_us` would hide a real oddity."""
        cases = [["retries_us", "count"], ["window_us", "ratio"],
                 ["depth_bytes", "count"]]
        assert _run(_TITLES, {"BGA_CASES": json.dumps(cases)}) == [
            "Retries us", "Window us", "Depth bytes"]

    def test_a_key_with_no_quantity_is_untouched(self):
        """Which is every label the page draws beside a sentence
        rather than a number."""
        cases = [["idle_us", None], ["total_bytes", None]]
        assert _run(_TITLES, {"BGA_CASES": json.dumps(cases)}) == [
            "Idle us", "Total bytes"]

    def test_a_key_that_is_only_its_unit_keeps_it(self):
        """`_us` alone is not a label, and an empty `<dt>` is worse
        than an ugly one."""
        assert _run(_TITLES, {"BGA_CASES": json.dumps(
            [["us", "duration_us"], ["bytes", "bytes"]])}) == ["Us", "Bytes"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
