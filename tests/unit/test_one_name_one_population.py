"""UX-1193: a preset and a section that share a name count one population.

Measured before, on the 1,202-element run (`--layers 20 --width 60`):
the preset "Latent heavies" drew 1,180 elements (`observed_critical ==
false`), and the section asking the same question published 0.
"""

import pytest

from bga import schemas
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

#: The table the presets are views of; its own question is the unfiltered view's.
TABLE = "elements"


def _pairs():
    """(preset, section key) for every preset naming a section: its question or its label."""
    props = schemas.schema(schemas.ANALYZE)["properties"]
    out = []
    for preset in props[TABLE][schemas.PRESETS]:
        for key, spec in props.items():
            if key == TABLE or not isinstance(spec, dict) or not spec.get("bga:question"):
                continue
            if preset["question"] == spec["bga:question"] or preset["name"] == key.replace("_", " ").capitalize():
                out.append((preset, key, spec))
    return out


def test_a_named_section_is_what_its_preset_reads():
    wrong = [
        (preset["name"], key, preset.get("from") or preset.get("where"))
        for preset, key, _ in _pairs()
        if not (preset.get("from") == key or str(preset.get("from", "")).startswith(key + "."))
    ]
    assert wrong == [], f"preset(s) sharing a section's name but reading another population: {wrong}"


def test_the_pairs_were_found():
    """So an empty pairing cannot pass the clause above."""
    names = {preset["name"] for preset, _, _ in _pairs()}
    assert {"Critical path", "Choke points", "Latent heavies"} <= names, names


#: Each list section's distinct elements, and each preset option's count.
_COUNTS = """(() => {
  const keys = %s;
  const offered = {};
  for (const o of document.querySelectorAll('select.preset-view option')) {
    const m = o.textContent.match(/\\((\\d[\\d,]*)\\)$/);
    offered[o.value] = m ? Number(m[1].replace(/,/g, '')) : null;
  }
  const published = {};
  for (const key of keys) {
    const s = document.querySelector(`section[data-section="${key}"]`);
    published[key] = s ? new Set([...s.querySelectorAll('td[data-column="element_uid"]')]
      .map((td) => td.dataset.raw)).size : 0;
  }
  return { offered, published };
})()"""


@pytest.fixture(scope="module")
def uris(tmp_path_factory):
    out = pages.pages(tmp_path_factory, prefix="population")
    into = tmp_path_factory.mktemp("population-1202")
    run = pages.two_plane_run(into, shape=("--layers", "20", "--width", "60"), name="big")
    out["1202"] = pages.export_uri(run, into / "page")
    return out


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
@pytest.mark.parametrize("label", [*sorted(pages.FIXTURES), "1202"])
def test_a_preset_counts_what_its_section_publishes(uris, label):
    lists = [(p, key) for p, key, spec in _pairs() if "array" in (spec.get("type") or [])]
    with Browser(find_chrome()) as browser:
        seen = browser.measure(uris[label], _COUNTS % [key for _, key in lists], 1440, 900)
    rows = [(p["name"], seen["offered"].get(p["name"]) or 0, seen["published"][key]) for p, key in lists]
    assert lists and all(drawn == published for _, drawn, published in rows), (
        f"{label}: (preset, drawn, section) {rows}"
    )
