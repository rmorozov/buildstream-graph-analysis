"""UX-1159 (styleguide §4g.2): a key path is text only where a reader copies it.

Every `description` of every `schemas.schema(name)` - not only those a
fixture reaches - names a field by its words, never by a `snake_case`
key, an `UPPER_CASE` constant or a dotted path. On `golden` and
`macro_micro`, every door open, no visible text node holds one outside
a copy surface: a `pre`, a command line, a Perfetto query's tables, a
`[data-copy]` control, the JSON door. A token a query beside it spells
is that query's own column.

UX-1166: at 1440 and 390, and on the two-plane review page too, no such
node holds a spaced hyphen for a dash; no description does either, and
no viewer or `shown.py` literal draws a dash for a null.

UX-1172: nor does a block's whole text or an accessible name, and
neither holds a leading "- ", "->", "**", "[]" or a raw YAML key; a
chain name wraps only at a separator; Markdown copy and the CLI say
their unit.
"""

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import schemas
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: A `snake_case` key, a dotted path (`headline.chain_share`, `rows[].x`) that is not a file name,
#: or a list step spelled `.[]` (`findings.[].evidence`).
_KEY = re.compile(
    r"(?<![\w-])[a-z][a-z0-9]*(?:_[a-z0-9]+)+(?![\w-])"
    r"|(?<![\w-])[a-z][a-z0-9_]*\.\[\]"
    r"|(?<![\w./:-])[a-z][a-z0-9_]+(?:\[[^\]]*\])?\.(?!(?:json|jsonl|md|js|py|conf|bst|gz|html|css|log|txt|status|[acsoh]|cpp)\b)[a-z_][a-z0-9_]*"
)
#: A bga constant; the kernel's and the loader's own names are theirs.
_CONSTANT = re.compile(r"(?<![\w-])[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+(?![\w-])")
_SYSTEM = {"LD_PRELOAD", "PT_INTERP"}


def _descriptions(node, where):
    if isinstance(node, dict):
        if isinstance(node.get("description"), str):
            yield where, node["description"]
        for key, value in node.items():
            yield from _descriptions(value, f"{where}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _descriptions(value, f"{where}[{index}]")


def _walked():
    return [(w, d) for name in schemas.names() for w, d in _descriptions(schemas.schema(name), name)]


def test_no_schema_description_names_a_key():
    walked = _walked()
    assert len(walked) > 1000, len(walked)
    named = [
        (where, found)
        for where, text in walked
        if (found := _KEY.findall(text) + [c for c in _CONSTANT.findall(text) if c not in _SYSTEM])
    ]
    assert named == [], named


#: A hyphen with a space on both sides and a word before it: a dash, not a list bullet.
_SPACED = re.compile(r"(?<=\S) - ")


def test_no_schema_description_spaces_a_hyphen():
    dashed = [(where, text[:80]) for where, text in _walked() if _SPACED.search(text)]
    assert dashed == [], dashed


#: A string literal that is only a dash - what a null used to print as.
_LONE_DASH = re.compile("([\"'`])[\u2014\u2013]\\1")


def test_no_null_is_drawn_as_a_dash():
    sources = [*sorted((REPO / "bga" / "viewer").glob("*.js")), REPO / "bga" / "shown.py"]
    lone = [
        f"{path.name}:{number}"
        for path in sources
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if _LONE_DASH.search(line.split("//")[0] if path.suffix == ".js" else line)
    ]
    assert len(sources) > 20, sources
    assert lone == [], lone


_READ = (
    "(() => {"
    + pages.OPEN_EVERY_DOOR_JS
    + """
  const copied = 'pre, script, style, [data-raw-json], [data-copy], .next-step, .query-needs, '
    + '.copy-step, body > header h1';
  // The run's own name is data wherever a path carries it; a section's queries are its own columns.
  const run = document.querySelector('body > header h1')?.textContent ?? '';
  const said = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const parent = n.parentElement;
    const text = n.textContent.trim();
    if (!text || !parent || parent.closest(copied) || !parent.checkVisibility()) continue;
    // A published string drawn as itself (a command a process ran) is data, not a label.
    const itself = parent.closest('[data-raw]')?.getAttribute('data-raw').trim() === text;
    const section = parent.closest('section[id]');
    const beside = [...(section?.querySelectorAll('pre') ?? [])].map((p) => p.textContent).join('\\n');
    said.push({ text, itself, section: section?.id ?? null, beside: `${run}\\n${beside}` });
  }
  // UX-1172: a block's text whole, since a dash can sit at a node's edge; and every name.
  const block = (p) => { while (p.parentElement && getComputedStyle(p).display.startsWith('inline')) p = p.parentElement; return p; };
  const blocks = new Set([...document.querySelectorAll('body *')].filter(
    (e) => !e.closest(copied) && e.checkVisibility() && [...e.childNodes].some((c) => c.nodeType === 3 && c.data.trim()))
    .map(block));
  const whole = [...blocks].map((b) => ({ text: b.innerText.replace(/\\s+/g, ' ').trim(), section: b.closest('section[id]')?.id ?? null }));
  const names = [...document.querySelectorAll('[aria-label], [title]')].filter((e) => e.checkVisibility())
    .flatMap((e) => ['aria-label', 'title'].map((a) => e.getAttribute(a)).filter(Boolean));
  // A wrap inside a chain name, not after its `/`.
  const inside = [];
  let wrapped = 0;
  document.querySelectorAll('.path-name').forEach((name) => {
    let last = null;
    let before = '';
    for (const t of [...name.childNodes].filter((c) => c.nodeType === 3)) {
      for (let i = 0; i < t.data.length; i += 1) {
        const r = document.createRange();
        r.setStart(t, i); r.setEnd(t, i + 1);
        const top = r.getBoundingClientRect().top;
        if (last !== null && top > last + 2) { wrapped += 1; if (before !== '/') inside.push(name.textContent); }
        last = top; before = t.data[i];
      }
    }
  });
  return { said, whole, names, inside, wrapped };
})()"""
)

#: Where a published string drawn as itself is still reader text: a path the schema says is one.
_READ_AS_LABEL = {"document_shape"}


@pytest.fixture(scope="module", params=[*sorted(pages.FIXTURES), "two_plane"])
def read(request, tmp_path_factory):
    tmp = tmp_path_factory.mktemp(f"copied-{request.param}")
    if request.param == "two_plane":
        uri = pages.export_uri(pages.two_plane_run(tmp, shape=pages.REVIEW_SHAPE), tmp / "page")
    else:
        uri = pages.export_uri(pages.FIXTURES[request.param], tmp)
    with Browser(chrome) as opened:
        return request.param, {width: opened.measure(uri, _READ, width=width, height=900) for width in (1440, 390)}


def _reader_text(out):
    return [node for node in out["said"] if not node["itself"] or node["section"] in _READ_AS_LABEL]


@needs_browser
def test_no_reader_text_holds_a_key_path(read):
    label, by_width = read
    for width, out in by_width.items():
        assert len(out["said"]) > 500, (label, width, len(out["said"]))
        keys = [
            (node["section"], key, node["text"][:120])
            for node in _reader_text(out)
            for key in _KEY.findall(node["text"])
            if key not in node["beside"]
        ]
        assert keys == [], (label, width, keys)


@needs_browser
def test_no_reader_text_spaces_a_hyphen_for_a_dash(read):
    label, by_width = read
    for width, out in by_width.items():
        dashed = [(node["section"], node["text"][:120]) for node in _reader_text(out) if _SPACED.search(node["text"])]
        assert dashed == [], (label, width, dashed)


#: A spaced hyphen, a leading bullet, an ASCII arrow, Markdown bold, a list step, a raw YAML key.
_RESIDUE = re.compile(r"(?<=\S) - |^- |->|\*\*|\[\]|\b[a-z_]+: [a-z_]+: ")


@needs_browser
def test_no_block_or_name_holds_ascii_residue(read):
    label, by_width = read
    for width, out in by_width.items():
        assert len(out["whole"]) > 300 and len(out["names"]) > 50, (label, width, len(out["whole"]), len(out["names"]))
        found = [(n["section"], n["text"][:120]) for n in out["whole"] if _RESIDUE.search(n["text"])]
        found += [("name", name[:120]) for name in out["names"] if _RESIDUE.search(name)]
        assert found == [], (label, width, found)


@needs_browser
def test_a_chain_name_wraps_at_a_separator(read):
    label, by_width = read
    assert label != "two_plane" or by_width[390]["wrapped"] > 0, "no chain name wraps: the guard reads nothing"
    for width, out in by_width.items():
        assert out["inside"] == [], (label, width, out["inside"])


node = shutil.which("node")


@pytest.mark.skipif(node is None, reason="node is not installed")
def test_markdown_copy_names_a_raw_unit():
    script = """
const shim = await import(process.env.BGA_DOM_SHIM);
shim.installDocument();
const { rowsMarkdown } = await import(process.env.BGA_TABLES);
const tr = shim.makeNode("tr");
const td = shim.makeNode("td");
td.setAttribute("data-column", "duration_us");
td.setAttribute("data-raw", "279000");
tr.append(td);
console.log(JSON.stringify(rowsMarkdown([tr], [{ key: "duration_us", title: "Duration", quantity: "duration_us" }])));
"""
    done = subprocess.run(
        [node, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=60,
        env={
            **os.environ,
            "BGA_DOM_SHIM": (REPO / "tests/dom_shim.mjs").as_uri(),
            "BGA_TABLES": (REPO / "bga/viewer/tables.js").as_uri(),
        },
    )
    assert done.returncode == 0, done.stderr[-2000:]
    assert json.loads(done.stdout).splitlines()[0] == "| Duration (\u00b5s) |"


def test_the_cli_spaces_its_unit(monkeypatch):
    from types import SimpleNamespace

    from bga import cli
    from bga.floors import cpu

    floor = {"lb_cpu_us": 1_500_000, "lb_cpu_binds": True, "lb_cpu_cores_source": "host", "lb_cpu_governing_cores": 4}
    monkeypatch.setattr(cpu, "compute_cpu_floor", lambda *_: dict(floor))
    result = SimpleNamespace(floors={"lb": 1})
    cli._add_cpu_floor(result, {}, None)
    assert "1.50 s," in result.floors["capacity_model_note"], result.floors["capacity_model_note"]
