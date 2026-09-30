"""UX-1141 (styleguide §4g.2): a reader sees a label, never a key.

Every door open on golden, macro_micro and the review's two-plane page:
no visible text node is a bare `snake_case`/`UPPER_CASE` token, no
Top-N option names a column by its key, no `dl` repeats a term.
`<code>` (a path or a command) and the run's own name are exempt;
`UX-1159` names `T_C` beside its words, so no floor row is.
"""

import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_READ = (
    "(() => {"
    + pages.OPEN_EVERY_DOOR_JS
    + pages.VISIBLE_TEXT_JS
    + """
  const options = [...document.querySelectorAll('select.top-n option')].map((o) => o.textContent);
  const repeated = [];
  document.querySelectorAll('dl').forEach((dl) => {
    const terms = [...dl.children].filter((c) => c.tagName === 'DT').map((c) => c.textContent.trim());
    terms.forEach((t, i) => { if (terms.indexOf(t) !== i) repeated.push(t); });
  });
  return { visible, options, repeated };
})()"""
)

_BARE_KEY = re.compile(r"^(?:[a-z][a-z0-9]*(?:_[a-z0-9]+)+|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)$")
_KEY_IN_OPTION = re.compile(r"\bby [a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
#: A dotted or bracketed key path, a `Resource.PROCESS` enum spelling, a `.jsonl` file name;
#: an element (`x_y.bst`) is data, not a key.
_KEY_PATH = re.compile(
    r"\b[A-Za-z0-9]+_[A-Za-z0-9_]*\.(?!bst\b)[A-Za-z_]+|\b[a-z][a-z0-9]*\.[a-z0-9]+_[a-z0-9_]+"
    r"|\w\[\d*\]|\b[A-Z][a-z]+\.[A-Z]{2,}\b|\b[\w-]+\.jsonl\b"
)
#: Buckets the payload keys by a single lowercase word, which the bare-token regex cannot see.
_ONE_WORD_KEYS = {"useful", "untracked"}


def _is_path_text(node):
    """A process command line and the schema drawing's own path rows are data, not reader text."""
    section = node["section"] or ""
    return bool(_KEY_PATH.search(node["text"])) and section != "document_shape" and not section.startswith("element-")


@pytest.fixture(scope="module", params=["golden", "macro_micro", "two_plane"])
def measured(request, tmp_path_factory):
    tmp = tmp_path_factory.mktemp(f"labels-{request.param}")
    if request.param == "two_plane":
        uri = pages.export_uri(pages.two_plane_run(tmp, shape=pages.REVIEW_SHAPE), tmp / "page")
        widths = (1440, 390)
    else:
        uri = pages.export_uri(pages.FIXTURES[request.param], tmp)
        widths = (1440,)
    with Browser(chrome) as opened:
        return {width: opened.measure(uri, _READ, width=width, height=900) for width in widths}


@needs_browser
class TestAReaderSeesLabelsNotKeys:
    def test_no_visible_text_node_is_a_bare_key(self, measured):
        for width, out in measured.items():
            assert len(out["visible"]) > 500, (width, len(out["visible"]))
            bare = [
                (n["section"], n["text"])
                for n in out["visible"]
                if _BARE_KEY.match(n["text"]) and not n["code"] and not n["header"]
            ]
            assert bare == [], (width, bare)

    def test_no_visible_text_holds_a_key_path_or_a_finding_id(self, measured):
        from bga.findings import FINDING_READERS

        ids = re.compile(
            r"(?<![\w-])(?:" + "|".join(map(re.escape, (i for i in FINDING_READERS if "-" in i))) + r")(?![\w-])"
        )
        for width, out in measured.items():
            said = [
                (n["section"], n["text"][:400])
                for n in out["visible"]
                if not n["code"] and (_is_path_text(n) or ids.search(n["text"]) or n["text"] in _ONE_WORD_KEYS)
            ]
            assert said == [], (width, said)

    def test_no_top_n_option_names_a_key(self, measured):
        for width, out in measured.items():
            assert out["options"], width
            keyed = [o for o in out["options"] if _KEY_IN_OPTION.search(o)]
            assert keyed == [], (width, keyed)

    def test_no_list_repeats_a_term(self, measured):
        for width, out in measured.items():
            assert out["repeated"] == [], (width, out["repeated"])
