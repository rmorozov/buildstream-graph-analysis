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
"""

import pathlib
import re
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
  return { said };
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
