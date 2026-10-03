"""UX-1175: the export drops indentation outside literals, and the page reads the same.

`_uncomment_js` drops a line's leading whitespace unless the line starts
inside a string, template or regex literal; `_uncommented_css` drops the
whitespace no selector or value reads. Golden's page half, `bga view
--export`: 151,228 -> 142,828 B.

Styleguide §3e.
"""

import json
import pathlib
import re
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

VIEWER = REPO / "bga/viewer"
MODULES = tuple(name for name in view.ASSETS if name.endswith(".js"))
STYLE = (VIEWER / "style.css").read_text(encoding="utf-8")


def _templates(text):
    return [text[start:end] for comment, start, end in view._lexed_spans(text) if not comment and text[start] == "`"]


def _old_css(text):
    """The stylesheet pass before `UX-1175`: comments and each line's indentation."""
    return "\n".join(line.strip() for line in re.sub(r"/\*.*?\*/", "", text, flags=re.S).splitlines() if line.strip())


class TestALiteralKeepsItsWhitespace:
    def test_a_built_literal_with_indented_content_survives(self):
        literal = "`select a,\n       b\n  from t\n\twhere ${\n    x}`"
        module = f"function f() {{\n    const q = {literal};\n    return '  x\\\n    y';\n}}"
        out = view._uncomment_js(module)
        assert literal in out, out
        assert "'  x\\\n    y'" in out, "a string continued over a line lost its indentation"
        assert out.startswith("function f() {\nconst q = `select a,"), out

    @pytest.mark.parametrize("name", MODULES)
    def test_every_template_literal_in_a_module_is_byte_identical(self, name):
        source = (VIEWER / name).read_text(encoding="utf-8")
        assert _templates(view._uncomment_js(source)) == _templates(source), name

    def test_the_modules_carry_an_indented_literal(self):
        indented = [t for name in MODULES for t in _templates((VIEWER / name).read_text(encoding="utf-8"))]
        indented = [t for t in indented if re.search(r"\n[ \t]+\S", t)]
        assert len(indented) >= 10, f"only {len(indented)} literals carry indented lines; the clause above is vacuous"


class TestCodeCarriesNoIndentation:
    def test_every_indented_line_of_the_module_starts_inside_a_literal(self):
        module = view._viewer_module()
        inside = set()
        for comment, start, end in view._lexed_spans(module):
            if not comment:
                inside.update(m.start() + 1 for m in re.compile("\n").finditer(module, start, end - 1))
        at, stray = 0, []
        for line in module.split("\n"):
            if line[:1] in (" ", "\t") and at not in inside:
                stray.append(line)
            at += len(line) + 1
        assert not stray, stray[:5]
        assert module.count("\n") > 5_000


class TestTheStylesheet:
    def test_its_strings_survive_and_its_indentation_does_not(self):
        css = view._uncommented_css(
            'a > b , c { content: " , ; : " ; margin: 0 ; }\n  d:hover {\n  x: calc(1px + 2px);\n}'
        )
        assert css == 'a > b,c{content:" , ; : ";margin:0}d:hover{x:calc(1px + 2px)}', css
        strings = re.findall(r"\"[^\"\n]*\"|'[^'\n]*'", _old_css(STYLE))
        assert re.findall(r"\"[^\"\n]*\"|'[^'\n]*'", view._uncommented_css(STYLE)) == strings

    @needs_browser
    def test_chromium_parses_the_same_rules(self, tmp_path):
        page = tmp_path / "blank.html"
        page.write_text("<!doctype html><title>css</title><p>two sheets</p>", encoding="utf-8")
        probe = """(() => {
          const rules = (text) => { const sheet = new CSSStyleSheet(); sheet.replaceSync(text);
            // A custom property keeps its value's raw whitespace; a comma's is never read.
            return [...sheet.cssRules].map((rule) => rule.cssText.replace(/,\\s+/g, ",")); };
          return { before: rules(@BEFORE@), after: rules(@AFTER@) };
        })()"""
        probe = probe.replace("@BEFORE@", json.dumps(_old_css(STYLE)))
        probe = probe.replace("@AFTER@", json.dumps(view._uncommented_css(STYLE)))
        with Browser(chrome) as browser:
            seen = browser.measure(page.as_uri(), probe)
        assert len(seen["before"]) > 300, len(seen["before"])
        changed = [(b, a) for b, a in zip(seen["before"], seen["after"]) if a != b]
        assert seen["after"] == seen["before"], (len(seen["before"]), len(seen["after"]), changed[:2])


def test_golden_page_half_is_5000_b_smaller(tmp_path, monkeypatch):
    written = {}
    for label in ("after", "before"):
        into = tmp_path / label
        into.mkdir()
        if label == "before":
            monkeypatch.setattr(view, "_unindented_js", lambda text: text)
            monkeypatch.setattr(view, "_uncommented_css", _old_css)
        written[label] = view.export(str(snapshot_copy(FIXTURES["golden"], into)), str(into / "r.html"))["page_bytes"]
    assert written["before"] - written["after"] >= 5_000, written
