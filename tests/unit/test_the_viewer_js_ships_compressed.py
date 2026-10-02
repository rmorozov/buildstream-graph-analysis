"""UX-1052: the export carries its viewer module gzipped, under a bound.

Measured on the two committed fixtures, `bga view --export`:

```text
                  page half (before -> after)   total (before -> after)
golden            342,017 -> 138,531 B          508,053 -> 304,567 B
macro_micro       342,017 -> 138,531 B          568,335 -> 364,849 B
```

The module is `_viewer_module()` byte for byte once inflated, so a stack
trace's `blob:` line is a line of that source; the served page is not
touched. `PAGE_BUDGET_B` is in `CEILINGS`, so cli.md's table carries it.
`UX-1167`, `UX-1233`: the owner raised it to 160,000 then 165,000 B; round 165 166,150 B.
"""

import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from pages import FIXTURES, snapshot_copy

from tests.browser import NO_BROWSER, Browser, find_chrome
from tools import bga_view as view

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


@pytest.fixture(scope="module")
def exports(tmp_path_factory):
    """`{label: (path, what export() returned)}` for the committed runs."""
    made = {}
    for label, fixture in sorted(FIXTURES.items()):
        into = tmp_path_factory.mktemp(f"gz-{label}")
        path = into / "report.html"
        made[label] = (path, view.export(str(snapshot_copy(fixture, into)), str(path)))
    return made


def test_the_page_half_is_under_its_bound(exports):
    for label, (path, written) in exports.items():
        html = path.read_text(encoding="utf-8")
        page = view.page_half(html)
        assert written["page_bytes"] == page, (label, written, page)
        assert written["page_bytes"] + written["data_bytes"] == written["bytes"]
        assert written["page_bytes"] < view.PAGE_BUDGET_B, (
            f"{label}: the page half is {written['page_bytes']:,} B, over "
            f"PAGE_BUDGET_B's {view.PAGE_BUDGET_B:,} - is the viewer module "
            f"still shipped gzipped?"
        )


def test_the_module_inflates_to_its_source_byte_for_byte(exports):
    for label, (path, _written) in exports.items():
        html = path.read_text(encoding="utf-8")
        assert view.inflated_module(html) == view._viewer_module(), label
        inline = re.findall(r'<script type="module">(.*?)</script>', html, re.S)
        assert len(inline) == 1 and len(inline[0]) < 2_000, (
            f"{label}: the one inline module is the loader, not the viewer"
        )


@needs_browser
def test_the_export_boots_and_a_stack_names_a_source_line(exports):
    """One `file://` load: a clean console, a booted page, and each
    `blob:` frame's line and column landing on `event.key` in the source."""
    path, _written = exports["golden"]
    probe = """(() => {
      const stacks = [];
      const event = new KeyboardEvent("keydown");
      Object.defineProperty(event, "key", {
        get() { stacks.push(new Error().stack); return "x"; } });
      document.dispatchEvent(event);
      const report = document.getElementById("report");
      return { busy: report.getAttribute("aria-busy"),
               sections: report.querySelectorAll("section").length,
               stacks };
    })()"""
    with Browser(chrome) as browser:
        seen = browser.observe(path.as_uri(), probe)
    assert seen["console"] == [] and seen["csp"] == [], seen
    value = seen["value"]
    assert value["busy"] == "false" and value["sections"] > 0, value
    lines = view.inflated_module(path.read_text(encoding="utf-8")).split("\n")
    frames = [
        (int(line), int(col))
        for stack in value["stacks"]
        for line, col in re.findall(r"\(blob:[^)]*:(\d+):(\d+)\)", stack)
    ]
    assert frames, f"no frame from the loaded module: {value['stacks']}"
    for line, col in frames:
        assert lines[line - 1][col - 1 :].startswith("key"), (
            f"blob line {line}:{col} is {lines[line - 1]!r}, not the source line that read `event.key`"
        )


@needs_node
def test_a_browser_without_decompression_says_so(tmp_path):
    """No `DecompressionStream`: a sentence in `#report`, not "Loading…"."""
    loader = view._MODULE_LOADER
    harness = tmp_path / "loader.mjs"
    harness.write_text(
        'delete globalThis.DecompressionStream;\n'
        'const { installDocument, makeNode } =\n'
        '  await import(process.env.BGA_DOM_SHIM);\n'
        'const report = makeNode("main");\n'
        'report.textContent = "Loading";\n'
        'report.setAttribute("aria-busy", "true");\n'
        'installDocument({ getElementById: (id) =>\n'
        '  id === "report" ? report : makeNode("script") });\n'
        'await import("data:text/javascript;base64," +\n'
        f'  Buffer.from({json.dumps(loader)}).toString("base64"));\n'
        'console.log(JSON.stringify({ textContent: report.textContent,\n'
        '                              attrs: report.attrs }));\n',
        encoding="utf-8",
    )
    done = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    report = json.loads(done.stdout)
    assert "DecompressionStream" in report["textContent"], report
    assert "aria-busy" not in report["attrs"], report
