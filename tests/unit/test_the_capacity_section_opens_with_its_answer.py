"""UX-1143: `#capacity_recommendation` opens with its answer, and the finding links to it.

The section drew four inputs, a constraints table and "Binding constraint
CPU", with no sentence saying what to set; the clamp from 31 was told only
in the finding's title, and the finding repeated the section's evidence.
"""

import functools
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.correlate import compute_capacity_recommendation
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

VIEWPORTS = [(1440, 900), (390, 844)]
_BUILD = {
    "two_plane": functools.partial(pages.two_plane_run, shape=("--layers", "8", "--width", "14"), name="two_plane"),
}

_READ = r"""
(() => {
  const section = document.querySelector('[data-section="capacity_recommendation"]');
  const card = document.getElementById("finding-capacity-recommendation");
  card?._hydrate?.();
  const label = (dt) => { const c = dt.cloneNode(true); c.querySelectorAll("button").forEach((b) => b.remove()); return c.textContent.trim(); };
  const own = section ? [...section.querySelectorAll(":scope > dl.pairs > dt")].map(label) : [];
  const links = [...document.querySelectorAll("a[data-section-link]")].map((a) => ({
    href: a.getAttribute("href"), resolves: Boolean(document.getElementById(a.getAttribute("href").slice(1))) }));
  return {
    section: Boolean(section),
    lead: section?.children[1]?.matches("p.section-lead") ? section.children[1].textContent : null,
    pairs: section ? [...section.querySelectorAll(":scope > dl.pairs > dt")].map(
      (dt) => [label(dt), dt.nextElementSibling?.querySelector("[data-raw]")?.dataset.raw ?? null]) : [],
    own,
    card: Boolean(card),
    cardTerms: card ? [...card.querySelectorAll("dt")].map(label) : [],
    cardLink: card?.querySelector("a[data-section-link]")?.getAttribute("href") ?? null,
    links,
  };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def uris(tmp_path_factory):
    root = tmp_path_factory.mktemp("capacity-answer")
    made = {label: pages.export_uri(pages.FIXTURES[label], root / label, f"{label}.html") for label in pages.FIXTURES}
    for label, make in _BUILD.items():
        into = root / label
        made[label] = pages.in_place_uri(make(into), into, f"{label}.html")
    yield made
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture(scope="module")
def read(browser, uris):
    return {
        (label, width): browser.measure(uri, _READ, width, height)
        for label, uri in uris.items()
        for width, height in VIEWPORTS
    }


@needs_browser
@pytest.mark.parametrize("label", ["two_plane", "macro_micro"])
@pytest.mark.parametrize("width", [w for w, _ in VIEWPORTS])
def test_the_section_opens_with_a_sentence_naming_the_count(read, label, width):
    got = read[(label, width)]
    assert got["section"], f"{label}: no capacity section to read"
    assert got["lead"], f"{label} @{width}: the section's first block is not its answer"
    recommended = dict(got["pairs"])["Recommended builders"]
    assert f" {recommended} builder" in got["lead"] or f" to {recommended}:" in got["lead"], (recommended, got["lead"])


@needs_browser
@pytest.mark.parametrize("label", ["two_plane", "macro_micro"])
@pytest.mark.parametrize("width", [w for w, _ in VIEWPORTS])
def test_the_finding_links_instead_of_repeating(read, label, width):
    got = read[(label, width)]
    assert got["card"], f"{label}: no capacity finding to read"
    repeated = sorted(set(got["cardTerms"]) & set(got["own"]))
    assert repeated == [], f"{label} @{width}: the finding repeats the section's {repeated}"
    assert got["cardLink"] == "#capacity_recommendation", got["cardLink"]


@needs_browser
@pytest.mark.parametrize("label", ["two_plane", *pages.FIXTURES])
def test_every_section_link_lands(read, label):
    dead = [link for link in read[(label, 1440)]["links"] if not link["resolves"]]
    assert dead == [], dead


def test_the_clamp_is_told_in_the_sentence():
    got = compute_capacity_recommendation(
        {"cores_busy": 0.5138, "host_cpu_count": 4}, {}, knee=8, knee_range_top=8, builders=4
    )
    assert got["verdict"].startswith("Keep 4 builders:"), got["verdict"]
    assert "could feed 31" in got["verdict"] and "cap, not load, binds" in got["verdict"], got["verdict"]
    assert "the graph allows 8" in got["verdict"], got["verdict"]


def test_a_raise_is_a_hypothesis_and_a_cut_is_a_cut():
    up = compute_capacity_recommendation({"cores_busy": 1.0, "host_cpu_count": 16}, {}, knee=6, builders=4)["verdict"]
    assert up.startswith("Try 6 builders, up from 4:") and "hypothesis to time" in up, up
    down = compute_capacity_recommendation({"cores_busy": 3.0, "host_cpu_count": 4}, {}, knee=2, builders=4)["verdict"]
    assert down.startswith("Lower builders from 4 to 2:"), down


def test_the_text_report_leads_with_the_same_sentence():
    from types import SimpleNamespace

    from bga.findings import _capacity_recommendation_finding

    block = compute_capacity_recommendation({"cores_busy": 0.5138, "host_cpu_count": 4}, {}, knee=8, builders=4)
    (finding,) = _capacity_recommendation_finding(SimpleNamespace(capacity_recommendation=block))
    assert finding["detail"][0].strip() == block["verdict"], finding["detail"][0]
    assert finding["section"] == "capacity_recommendation"
