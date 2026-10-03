"""UX-1224: a filtered table prints the filter it is under, beside its badge.

Measured before, print media on the 1,202 two-plane page after "+1,160 more": the badge printed
"25 of 1,200 matched", the box was dropped, and no filter text reached paper.

Styleguide §2b.
"""

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

SHAPE = ("--layers", "20", "--width", "60")

# Unfiltered first, then the card's "+N more" pressed: the badge's text, attribute and print-media ::after each time.
_PRINTED = """(() => {
  const badge = document.querySelector('table[data-table="elements"]').parentNode.querySelector(".table-tools .badge");
  const read = () => ({ text: badge.textContent, filter: badge.getAttribute("data-filter"),
                        after: getComputedStyle(badge, "::after").content, shown: badge.checkVisibility() });
  const before = read();
  const more = document.querySelector('section[data-element="toolchain.bst"] a[data-more]');
  more.click();
  return { print: matchMedia("print").matches, more: more.textContent, before, after: read() };
})()"""


@pytest.fixture(scope="module")
def uris(tmp_path_factory):
    into = tmp_path_factory.mktemp("ux1224")
    return {
        label: pages.export_uri(pages.two_plane_run(into, shape, name=label), into / label)
        for label, shape in (("both", SHAPE), ("binaries", ("--workload", "binaries", *SHAPE)))
    }


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
def test_a_printed_filtered_table_states_its_filter(uris):
    """Under print media the elements badge's ::after carries the filter text; an unfiltered badge has none."""
    with Browser(find_chrome()) as browser:
        got = {
            (label, width): browser.measure(f"{uri}#element-toolchain-bst", _PRINTED, width, 900, media="print")
            for label, uri in uris.items()
            for width in (1440, 390)
        }
    for at, read in got.items():
        assert read["print"] and read["more"] == "+1,160 more", (at, read)
        assert read["before"]["filter"] is None and read["before"]["after"] == "none", (at, read)
        after = read["after"]
        assert "matched" in after["text"] and after["shown"], (at, read)
        assert after["filter"] == "depends_on:toolchain.bst", (at, read)
        assert after["after"] == '" - filter: depends_on:toolchain.bst"', (at, read)
