"""UX-1141 (styleguide §4g.2): a reader sees a label, never a key.

Every door open on golden, macro_micro and the review's two-plane page:
no visible text node is a bare `snake_case`/`UPPER_CASE` token, no
Top-N option names a column by its key, no `dl` repeats a term.
`<code>` (a path or a command) and the run's own name are exempt, and
`T_C` is `UX-1144`'s floor row.
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
#: `UX-1144` renames the floors; `T_C` is its row, not this one's.
_OWNED_ELSEWHERE = {"T_C"}


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
                if _BARE_KEY.match(n["text"])
                and not n["code"]
                and not n["header"]
                and n["text"] not in _OWNED_ELSEWHERE
            ]
            assert bare == [], (width, bare)

    def test_no_top_n_option_names_a_key(self, measured):
        for width, out in measured.items():
            assert out["options"], width
            keyed = [o for o in out["options"] if _KEY_IN_OPTION.search(o)]
            assert keyed == [], (width, keyed)

    def test_no_list_repeats_a_term(self, measured):
        for width, out in measured.items():
            assert out["repeated"] == [], (width, out["repeated"])
