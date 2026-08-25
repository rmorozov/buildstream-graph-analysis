"""UX-281 and UX-282: the satellite pages are part of the document.

Reported: *"sql.html doesn't have backlink to main page."* Checked
across every served page, and it was both of them:

```text
$ curl -s :PORT/sql.html      | grep -oE 'href="[^"]*"' | sort -u
href="perfetto.html"
href="style.css"

$ curl -s :PORT/perfetto.html | grep -oE 'href="[^"]*"' | sort -u
href="#"
href="https://ui.perfetto.dev"
href="style.css"
href="timeline.json.gz"
```

The report links out to both; neither linked home. `perfetto.html`
reached nothing inside the report at all - its only internal href was
`#`. The Back button works and is not the point: these pages are reached
*from* the report, are about the report, and carry its header and
stylesheet, so a page that cannot return to it reads as a different
site.

`UX-282` is the other half of the same page. *"Nothing opened? Use the
direct link"* sat three paragraphs under the button it is about - and
the only reader it exists for is mid-handoff, having just watched that
button fail.

The sweep runs over the **served set** rather than a list, so a page
added later is covered by construction.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
VIEWER = REPO / "bga/viewer"

# The one page that *is* the report. Everything else served as HTML has
# to be able to reach it.
HOME = "index.html"


def _served_pages():
    """Every `.html` the server answers, read from its own table."""
    import tools.bga_view as view

    return [name for name in view.ASSETS if name.endswith(".html")]


class TestEveryServedPageIsInTheDocument:
    def test_the_sweep_reads_the_servers_own_table(self):
        """`UX-281` item 3: over the served set, not a list. A page
        added to `ASSETS` later is covered without editing this file -
        which is the property a hand-written list would not have."""
        pages = _served_pages()
        assert HOME in pages, pages
        assert len(pages) >= 3, (
            f"only {pages} are served as HTML; this guard was written when "
            f"there were three")

    @pytest.mark.parametrize("page", [p for p in _served_pages() if p != HOME])
    def test_it_reaches_the_report_in_one_click(self, page):
        text = (VIEWER / page).read_text(encoding="utf-8")
        links = re.findall(r'href="([^"]+)"', text)
        assert HOME in links, (
            f"{page} links to {sorted(set(links))} and never home")

    @pytest.mark.parametrize("page", [p for p in _served_pages() if p != HOME])
    def test_the_link_says_where_it_goes(self, page):
        """Not "back": the reader may have arrived from a bookmark, and
        a browser already has a Back button."""
        text = (VIEWER / page).read_text(encoding="utf-8")
        found = re.search(r'<a href="index\.html"[^>]*>(.*?)</a>', text,
                          re.S)
        assert found, f"{page} has no home link to read"
        label = re.sub(r"\s+", " ", found.group(1)).strip().lower()
        assert "report" in label, f"{page}'s home link reads {label!r}"
        assert "back" not in label, f"{page}'s home link reads {label!r}"

    def test_the_report_still_links_out_to_them(self):
        """The other direction, so this cannot be satisfied by cutting
        the links that made the satellites reachable in the first
        place."""
        text = (VIEWER / HOME).read_text(encoding="utf-8")
        assert "sql.html" in text, "the report no longer offers the questions"


class TestTheHandoffFallbackIsBesideTheButton:
    def test_the_fallback_follows_the_button_in_one_row(self):
        """`UX-282` item 1. Beside it at wide widths, under it at narrow
        ones - `UX-272`'s pattern, and its breakpoint, so the page has
        one responsive vocabulary rather than its own."""
        text = (VIEWER / "perfetto.html").read_text(encoding="utf-8")
        row = re.search(r'<div class="handoff">(.*?)</div>', text, re.S)
        assert row, "the button and its fallback are not one row"
        body = row.group(1)
        assert 'id="open"' in body, "the button is not in the row"
        assert 'id="deep"' in body, "the fallback link is not in the row"
        assert body.index('id="open"') < body.index('id="deep"'), (
            "the fallback comes first, so a reader who has not pressed the "
            "button is offered two doors")

    def test_it_uses_the_same_breakpoint_as_the_header(self):
        css = (VIEWER / "style.css").read_text(encoding="utf-8")
        handoff = css.split(".handoff {", 1)
        assert len(handoff) == 2, "the row has no rule"
        after = handoff[1]
        assert "@media (max-width: 60rem)" in after, (
            "the hand-off row does not stack at `UX-272`'s breakpoint")

    def test_the_fallback_still_reads_as_a_fallback(self):
        """`UX-282` item 2: the primary path is the button. The line is
        conditional prose - it only makes sense to somebody for whom it
        did not work."""
        text = (VIEWER / "perfetto.html").read_text(encoding="utf-8")
        row = re.search(r'<div class="handoff">(.*?)</div>', text, re.S)
        assert "Nothing opened?" in row.group(1), (
            "the fallback no longer says it is one")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
