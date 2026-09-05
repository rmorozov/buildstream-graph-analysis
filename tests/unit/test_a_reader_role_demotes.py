"""UX-643: the role decides what is promoted, never what exists.

`READERS` carried five roles and the page showed all five everything;
the selector's only effect was one lead finding in one slot. A filter
was refused because the map is incomplete - 11 sections of 51 have a
derivable role - and because "hide what is not mine" collides with two
standing rules: focus never removes, and marks are never a filter.

So the role **demotes**. Measured on the exported page, sections
promoted and expanded against sections folded into `UX-347`'s chapter
and `UX-199`'s section fold:

```text
                 sections   R1   R2   R3   R4   R5
golden                 46    6    1    2    2    -
macro_micro            66    6    2    2    3    1
```

The rest of every column is folded and none of it is removed: the DOM
node count and every section's text are identical under all five roles
and back at "anyone".

**The map is derived, not judged.** `schemas._SECTION_READERS` is the
join of `provenance._CLAIMS`' evidence paths with
`findings.FINDING_READERS`, and the first clause below recomputes it -
a finding that changes reader reddens here rather than leaving a stale
role on the page.

**A browser guard** for everything below that: `data-collapsed` and
`data-open` are CSS, and whether a folded section is still reachable is
a question about layout that `tests/dom_shim.mjs` cannot answer.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)


def _derived():
    """`{section key: {role}}`, recomputed from the two tables.

    The section a finding's evidence lives in is the first segment of
    its `provenance` path; the reader is `FINDING_READERS`'. Two shapes
    contribute nothing and both are the map being incomplete rather
    than this join being wrong: `graph-width` and `memory-envelope`
    publish an empty path tuple, and `wait-category`,
    `blast-radius-reach` and `blast-radius-structural` compute their
    paths from the document, so there is no static answer to read.
    """
    from bga import findings, provenance

    role = {uid: short for uid, short, _label, _question in findings.READERS}
    joined = {}
    for finding, reader in findings.FINDING_READERS.items():
        claim = provenance._CLAIMS.get(finding)
        paths = claim[0] if claim else ()
        if not isinstance(paths, (tuple, list)):
            continue
        for path in paths:
            joined.setdefault(re.split(r"[.\[]", path)[0], set()).add(role[reader])
    return joined


class TestTheMapIsDerivedNotJudged:
    def test_the_table_is_the_join_of_the_two_it_reads(self):
        """The whole producer half. `total_duration_us` is in the join
        and is a scalar rather than a section, so it is the one key the
        table drops - stated here so dropping a second one reddens."""
        from bga import schemas

        joined = _derived()
        assert set(joined) - set(schemas._SECTION_READERS) == {"total_duration_us"}
        typed = {key: set(roles)
                 for key, roles in schemas._SECTION_READERS.items()}
        derived = {key: roles for key, roles in joined.items()
                   if key != "total_duration_us"}
        assert typed == derived, (
            "the authored map and the join of `provenance._CLAIMS` with "
            f"`findings.FINDING_READERS` disagree: typed {typed}, "
            f"derived {derived}")

    def test_every_declared_role_is_one_the_roster_has(self):
        """A section cannot serve a reader `findings.READERS` does not
        name; `READER_ROLES` is read off the roster for that reason."""
        from bga import schemas

        said = {role for roles in schemas._SECTION_READERS.values()
                for role in roles}
        assert said <= set(schemas.READER_ROLES), said - set(schemas.READER_ROLES)
        assert len(said) == len(schemas.READER_ROLES), (
            f"only {sorted(said)} of {list(schemas.READER_ROLES)} are served "
            f"by any section; a role no section serves is a role the picker "
            f"offers an empty page to")


#: Drive the picker through every option and read the page each time.
#:
#: `textOf` reads the document's words and no control's own label: the
#: `R1`-`R5` tag this item adds, and `UX-199`'s collapse caret, which is
#: `▾` open and `▸` shut and would report "the text changed" on every
#: fold. `decision` is excluded from the comparison for the same reason
#: one level up - `UX-372` already swaps a lead finding into it, which
#: is a change this item did not make.
_DRIVE = r"""
(() => {
  const textOf = (node) => {
    if (node.nodeType === 3) return node.textContent || "";
    if (node.nodeType !== 1) return "";
    if (node.hasAttribute("data-reader-tag")) return "";
    if (node.hasAttribute("data-collapse")) return "";
    return [...node.childNodes].map(textOf).join("");
  };
  const shape = () => {
    const sections = [...document.querySelectorAll("section[data-section]")];
    return {
      nodes: document.querySelectorAll("*").length,
      keys: sections.map((s) => s.getAttribute("data-section")),
      text: sections
        .filter((s) => s.getAttribute("data-section") !== "decision")
        .map((s) => textOf(s).replace(/\s+/g, " ").trim()).join(" | "),
      promoted: sections.filter((s) => s.hasAttribute("data-promoted"))
        .map((s) => s.getAttribute("data-section")),
      folded: sections.filter(
        (s) => s.getAttribute("data-collapsed") === "true"
               || s.closest('section.chapter[data-open="false"]'))
        .map((s) => s.getAttribute("data-section")),
      tagged: sections.filter(
        (s) => (s.querySelector("[data-reader-tag]")?.textContent || "").trim())
        .map((s) => s.getAttribute("data-section")),
      declares: Object.fromEntries(sections.map((s) => [
        s.getAttribute("data-section"),
        (s.querySelector("[data-reader-tag]")?.getAttribute("data-readers")
         || "").split(/\s+/).filter(Boolean)])),
    };
  };
  const select = document.querySelector("select[data-role=reader]");
  if (!select) return { picker: false };
  const landed = shape();
  const roles = {};
  for (const option of [...select.options].filter((o) => o.value)) {
    select.value = option.value;
    select.dispatchEvent(new Event("change"));
    roles[option.value] = {
      ...shape(),
      tag: document.querySelector("[data-role=reader-lead]")
             ?.getAttribute("data-reader") || null,
      role: [...document.querySelectorAll("[data-promoted]")]
        .map((n) => n.getAttribute("data-promoted"))[0] ?? null,
    };
  }

  // Reachability, under the last role chosen: an unmapped section in a
  // shut chapter, opened the way a reader opens it - the chapter's own
  // control, then the section's. Both already existed; neither is this
  // item's.
  const unmapped = [...document.querySelectorAll("section[data-section]")]
    .find((s) => !s.querySelector("[data-reader-tag]")
                 && s.closest('section.chapter[data-open="false"]'));
  let reached = null;
  if (unmapped) {
    const box = unmapped.closest("section.chapter");
    const before = unmapped.getAttribute("data-collapsed");
    box.querySelector("[data-chapter-open]")?.click();
    // Pressed only when it is shut, which is what a reader does with a
    // fold. Blind pressing would make this clause fail whenever the
    // fold above it did, and read as a reachability defect.
    if (unmapped.getAttribute("data-collapsed") === "true") {
      unmapped.querySelector("[data-collapse]")?.click();
    }
    reached = {
      key: unmapped.getAttribute("data-section"), before,
      collapsed: unmapped.getAttribute("data-collapsed"),
      chapterOpen: box.getAttribute("data-open"),
      height: unmapped.offsetHeight,
      words: (unmapped.textContent || "").trim().split(/\s+/).length,
    };
  }

  select.value = "";
  select.dispatchEvent(new Event("change"));
  return { picker: true, landed, roles, reached, anyone: shape() };
})()
"""


@pytest.fixture(scope="module")
def driven(tmp_path_factory):
    with Browser(chrome) as opened:
        return {label: opened.measure(uri, _DRIVE, 1440, 900)
                for label, uri in pages.pages(tmp_path_factory, "role").items()}


@needs_browser
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestARoleDemotesRatherThanHides:
    def test_a_role_promotes_what_it_serves_and_folds_the_rest(self, driven,
                                                              label):
        """The item. Every section declaring the chosen role is promoted
        and expanded; every other section on the page is folded, whether
        it declares another role or none at all."""
        page = driven[label]
        assert page["picker"], "no reader picker - nothing below measures"
        assert len(page["roles"]) >= 4, sorted(page["roles"])
        for chosen, seen in page["roles"].items():
            role = seen["role"]
            assert role, f"{chosen} promoted nothing and named no role"
            want = sorted(key for key, roles in seen["declares"].items()
                          if role in roles)
            assert want, f"{chosen}: no section declares {role}"
            assert sorted(seen["promoted"]) == want, (chosen, seen["promoted"])
            expanded = set(seen["keys"]) - set(seen["folded"])
            assert expanded - set(want) - {"decision"} == set(), (
                f"{chosen}: {sorted(expanded - set(want) - {'decision'})} are "
                f"expanded and are not this role's")
            assert set(want) - set(seen["folded"]) == set(want), (
                f"{chosen}: a promoted section is folded: "
                f"{sorted(set(want) & set(seen['folded']))}")

    def test_nothing_is_removed_and_no_sections_text_changes(self, driven,
                                                             label):
        """Focus never removes, and the export stays Ctrl-F honest. The
        node count moves only by `UX-372`'s lead block, which is four
        nodes and is added rather than taken away."""
        page = driven[label]
        landed = page["landed"]
        for chosen, seen in page["roles"].items():
            assert seen["keys"] == landed["keys"], (
                f"{chosen}: the section list changed")
            assert seen["text"] == landed["text"], (
                f"{chosen}: a section's text changed - "
                f"{len(seen['text'])} chars against {len(landed['text'])}")
            assert seen["nodes"] >= landed["nodes"], (
                f"{chosen}: {landed['nodes'] - seen['nodes']} DOM nodes were "
                f"removed; the role demotes and must not hide")

    def test_the_tag_is_worn_only_by_the_promoted(self, driven, label):
        """`UX-305`: emphasis is a budget spent once. The mark is on the
        sections one chosen role owns - never on the eight or ten that
        declare a role, and never on all 46 or 66."""
        page = driven[label]
        for chosen, seen in page["roles"].items():
            assert sorted(seen["tagged"]) == sorted(seen["promoted"]), (
                chosen, seen["tagged"], seen["promoted"])
            declaring = [k for k, r in seen["declares"].items() if r]
            assert len(seen["tagged"]) < len(declaring) + 1
            assert len(seen["tagged"]) < len(seen["keys"]) / 2, (
                f"{chosen} marks {len(seen['tagged'])} of {len(seen['keys'])} "
                f"sections; that is a page of emphasis, not a budget")

    def test_an_unmapped_section_stays_reachable(self, driven, label):
        """A section with no declared role is folded under every role -
        and two presses of controls that already existed put it back on
        screen, with its words."""
        page = driven[label]
        reached = page["reached"]
        assert reached, "no unmapped section was folded into a shut chapter"
        assert reached["chapterOpen"] == "true", reached
        assert reached["collapsed"] == "false", reached
        assert reached["height"] > 0, (
            f"{reached['key']} is folded and cannot be brought back on "
            f"screen: {reached}")
        assert reached["words"] > 3, reached

    def test_anyone_promotes_nothing_and_restores_the_landed_page(self,
                                                                  driven,
                                                                  label):
        """`UX-372`'s rule kept: with nobody chosen the page is what it
        was. Node count, section list, folds and marks all return."""
        page = driven[label]
        landed, anyone = page["landed"], page["anyone"]
        assert anyone["promoted"] == [], anyone["promoted"]
        assert anyone["tagged"] == [], anyone["tagged"]
        assert anyone["keys"] == landed["keys"]
        assert anyone["nodes"] == landed["nodes"], (anyone["nodes"],
                                                    landed["nodes"])
        assert sorted(anyone["folded"]) == sorted(landed["folded"]), (
            f"the fold did not come back: "
            f"{sorted(set(anyone['folded']) ^ set(landed['folded']))[:5]}")


#: `UX-650`: the second source, read the same way as the first.
#:
#: The eleven payload sections' roles are *derived* - the join above
#: recomputes them. A page-built section is published by no contract, so
#: its role is **declared at the construction site**, which is a weaker
#: source and therefore a stricter clause: every site either declares or
#: says at the site why it does not, and no site is left silent.
_BUILT_IN = ("bga/viewer/views.js", "bga/viewer/element.js",
             "bga/viewer/questions.js")

#: The two shapes a section is constructed in, and the two the reader is
#: declared in. `data-section` is the page's own key for a section
#: (`UX-199`), so a new one cannot avoid this parse by spelling.
_SITE = re.compile(r'"data-section"\s*[,:]\s*(?:"([^"]+)"|([^,}\)\n]+))')
_DECLARES = re.compile(r'declareReaders\([^,]+,\s*\[([^\]]*)\]\)')
_UNMAPPED = re.compile(r"UX-650`?:\s*\*\*unmapped, deliberately\.\*\*"
                       r"([^\n]*\n(?:\s*//[^\n]*\n)*)")
_FUNCTION = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)",
                       re.MULTILINE)


def _sites():
    """`{function name: (key, roles or None, reason)}` over the three
    page-building modules.

    Split on the top-level `function` seams the module graph already
    uses, because a construction site's declaration is in the function
    that builds the section and nowhere else - a file-wide search would
    let `renderOverview` pass on `renderEvidence`'s declaration.
    """
    found = {}
    for name in _BUILT_IN:
        text = (REPO / name).read_text(encoding="utf-8")
        starts = [m.start() for m in _FUNCTION.finditer(text)]
        for index, start in enumerate(starts):
            end = starts[index + 1] if index + 1 < len(starts) else len(text)
            body = text[start:end]
            keys = [(m.group(1) or m.group(2)).strip()
                    for m in _SITE.finditer(body)]
            if not keys:
                continue
            roles = [role.strip().strip('"')
                     for m in _DECLARES.finditer(body)
                     for role in m.group(1).split(",") if role.strip()]
            excuse = _UNMAPPED.search(body)
            found[f"{name.rsplit('/', 1)[1]}::{_FUNCTION.match(body).group(1)}"] = (
                keys[0], roles or None, excuse.group(1) if excuse else None)
    return found


#: What the sites declare, keyed the way the page keys them - the half
#: of `_sites()` a rendered page can be held against.
def _declared_by_key():
    return {key: roles for key, roles, _why in _sites().values() if roles}


class TestEveryPageBuiltSectionDecidesItsReader:
    def test_the_parse_reaches_the_sites_it_is_written_over(self):
        """The clause's own setup, asserted rather than assumed: a parse
        that matched nothing would pass every clause below it."""
        sites = _sites()
        assert len(sites) >= 13, sorted(sites)
        assert {"views.js::renderBlastSearch", "views.js::renderOverview",
                "element.js::renderHorizon",
                "questions.js::renderQuestions"} <= set(sites), sorted(sites)

    def test_no_site_is_silent(self):
        """The item. A section the page builds either names its reader
        at the site or says there why it cannot - and the refusal is a
        reason, not a marker: `UX-643` refused five payload sections and
        wrote down why for each."""
        for site, (key, roles, why) in sorted(_sites().items()):
            assert roles or why is not None, (
                f"{site} builds section {key!r} and neither declares a "
                f"reader nor says why it does not")
            if roles is None:
                assert len(" ".join(why.split())) > 80, (
                    f"{site} is unmapped with no reason worth reading: "
                    f"{why!r}")

    def test_every_declared_role_is_one_the_roster_has(self):
        """The same rule the derived half is held to, over the source
        this half is declared in."""
        from bga import schemas

        for site, (key, roles, _why) in sorted(_sites().items()):
            if not roles:
                continue
            assert set(roles) <= set(schemas.READER_ROLES), (
                f"{site} declares {sorted(set(roles) - set(schemas.READER_ROLES))} "
                f"for {key!r}, which `findings.READERS` does not name")


@needs_browser
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestTheDeclarationReachesThePage:
    def test_the_page_carries_what_the_site_declared(self, driven, label):
        """Source and page, one comparison. A declaration that does not
        reach the DOM is a role the picker cannot act on, and a role on
        the page that no site declared is a second mechanism."""
        declared = _declared_by_key()
        landed = driven[label]["landed"]["declares"]
        on_page = {key: roles for key, roles in landed.items()
                   if key in declared}
        assert len(on_page) >= 5, (
            f"{label}: only {sorted(on_page)} of the page-built sections "
            f"that declare a role rendered; nothing below measures")
        for key, roles in sorted(on_page.items()):
            assert roles == declared[key], (
                f"{label}: {key} carries {roles} and its site declares "
                f"{declared[key]}")

    def test_an_unmapped_page_built_section_declares_nothing(self, driven,
                                                             label):
        """The other half: a section whose site refused stays unmapped on
        the page, folded under every role and reachable under all - the
        behaviour `UX-643` designed for an incomplete map."""
        declared = _declared_by_key()
        landed = driven[label]["landed"]["declares"]
        for key in ("overview", "perfetto-questions"):
            assert key in landed, f"{label}: {key} is not on the page"
            assert not landed[key], (
                f"{label}: {key} declares {landed[key]} and its site says "
                f"it is unmapped")
        assert not declared.keys() & {"overview", "perfetto-questions"}
        elements = [key for key in landed if key.startswith("element-")]
        assert elements, f"{label}: no element section to check"
        assert all(not landed[key] for key in elements), (
            f"{label}: an element block declares a reader; the page cannot "
            f"tell which element is the reader's")
