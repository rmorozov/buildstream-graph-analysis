"""UX-1159 (styleguide §4g.2): a key path is text only where a reader copies it.

Every `description` of every `schemas.schema(name)` - not only those a
fixture reaches - names a field by its words, never by a `snake_case`
key, an `UPPER_CASE` constant or a dotted path. On `golden` and
`macro_micro`, every door open, no visible text node holds one outside
a copy surface: a `pre`, a command line, a Perfetto query's tables, a
`[data-copy]` control, the JSON door, the schema drawing. A token a
query beside it spells is that query's own column.
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

#: A `snake_case` key, or a dotted path (`headline.chain_share`, `rows[].x`) that is not a file name.
_KEY = re.compile(
    r"(?<![\w-])[a-z][a-z0-9]*(?:_[a-z0-9]+)+(?![\w-])"
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


def test_no_schema_description_names_a_key():
    walked = [(w, d) for name in schemas.names() for w, d in _descriptions(schemas.schema(name), name)]
    assert len(walked) > 1000, len(walked)
    named = [
        (where, found)
        for where, text in walked
        if (found := _KEY.findall(text) + [c for c in _CONSTANT.findall(text) if c not in _SYSTEM])
    ]
    assert named == [], named


_READ = (
    "(() => {"
    + pages.OPEN_EVERY_DOOR_JS
    + """
  const copied = 'pre, script, style, [data-raw-json], [data-copy], .next-step, .query-needs, '
    + '.copy-step, #document_shape, body > header h1';
  // The run's own name is data wherever a path carries it; a section's queries are its own columns.
  const run = document.querySelector('body > header h1')?.textContent ?? '';
  const said = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const parent = n.parentElement;
    const text = n.textContent.trim();
    if (!text || !parent || parent.closest(copied) || !parent.checkVisibility()) continue;
    // A published string drawn as itself (a command a process ran) is data, not a label.
    if (parent.closest('[data-raw]')?.getAttribute('data-raw').trim() === text) continue;
    const section = parent.closest('section[id]');
    const beside = [...(section?.querySelectorAll('pre') ?? [])].map((p) => p.textContent).join('\\n');
    said.push({ text, section: section?.id ?? null, beside: `${run}\\n${beside}` });
  }
  return { said };
})()"""
)


@pytest.fixture(scope="module", params=sorted(pages.FIXTURES))
def read(request, tmp_path_factory):
    uri = pages.export_uri(pages.FIXTURES[request.param], tmp_path_factory.mktemp(f"copied-{request.param}"))
    with Browser(chrome) as opened:
        return request.param, opened.measure(uri, _READ, width=1440, height=900)


@needs_browser
def test_no_reader_text_holds_a_key_path(read):
    label, out = read
    assert len(out["said"]) > 500, (label, len(out["said"]))
    keys = [
        (node["section"], key, node["text"][:120])
        for node in out["said"]
        for key in _KEY.findall(node["text"])
        if key not in node["beside"]
    ]
    assert keys == [], (label, keys)
