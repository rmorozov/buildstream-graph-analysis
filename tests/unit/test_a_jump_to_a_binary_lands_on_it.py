"""UX-1225: a jump to a binary lands on by_binary filtered to it, and its row links binary_cost filtered to it.

Measured before, on the 1,202-element `--workload binaries` page: a jump to lognormal-308 landed on by_binary
unfiltered ("25 of 601"); an unmounted binary was filtered into binary_cost instead.

Styleguide §3c.
"""

import collections

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

SHAPE = ("--workload", "binaries", "--layers", "20", "--width", "60")

# A binary by_binary mounts at rest and one it does not, each jumped to; by_binary's badge and box, then a row's link.
_JUMP = """(async () => {
  const turn = (ms = 50) => new Promise((done) => setTimeout(done, ms));
  const tools = (t) => document.querySelector(`table[data-table="${t}"]`).parentNode.querySelector(".table-tools");
  const read = (t) => [tools(t).querySelector(".badge").textContent, tools(t).querySelector("input.table-filter").value];
  const jump = document.getElementById("jump");
  const mounted = [...document.querySelectorAll("#by_binary tr[data-binary]")].pop().dataset.binary;
  let unmounted = null;
  for (let i = 0; !unmounted && i < 1000; i += 1) {
    jump.value = `lognormal-${String(i).padStart(3, "0")}`;
    jump.dispatchEvent(new Event("input", { bubbles: true }));
    unmounted = [...document.querySelectorAll(".jump-hits button[data-jump^='lognormal-']")].map((b) => b.dataset.jump)
      .find((name) => !document.querySelector(`#by_binary [data-binary="${name}"]`)) ?? null;
  }
  const landed = {};
  for (const key of [mounted, unmounted]) {
    jump.value = key;
    jump.dispatchEvent(new Event("input", { bubbles: true }));
    [...document.querySelectorAll(".jump-hits button[data-jump]")].find((b) => b.dataset.jump === key).click();
    await turn(600);
    landed[key] = { hash: location.hash.split("~")[0], by_binary: read("by_binary") };
  }
  document.querySelector(`#by_binary tr[data-binary="${unmounted}"] td[data-column="binary"] a`)?.click();
  await turn(300);
  return { landed, unmounted, linked: read("binary_cost") };
})()"""


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    into = tmp_path_factory.mktemp("ux1225")
    run = pages.two_plane_run(into, SHAPE, name="binaries")
    return run, pages.export_uri(run, into / "page")


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
def test_a_jump_to_a_binary_lands_on_it(page):
    """Mounted or not, by_binary reads "1 matched" under `binary:<key>`, not "25 of 601"; its link filters binary_cost."""
    from tools.bga_view import payloads

    run, uri = page
    report = payloads(str(run))["report.json"]
    ran = collections.Counter(row["binary"] for row in report["binary_cost"])
    with Browser(find_chrome()) as browser:
        got = {width: browser.measure(uri, _JUMP, width, 900) for width in (1440, 390)}
    for width, read in got.items():
        assert len(read["landed"]) == 2, (width, read)
        for key, landed in read["landed"].items():
            assert key in {row["binary"] for row in report["by_binary"]}, (width, read)
            assert landed == {"hash": "#by_binary", "by_binary": ["1 matched", f"binary:{key}"]}, (width, read)
        key = read["unmounted"]
        assert ran[key] > 1 and read["linked"] == [f"{ran[key]:,} matched", f"binary:{key}"], (width, read)


# UX-1261: binary_cost's answer names by_binary's leader; its link is that binary, and one click lands on its row.
_ANSWER = """(async () => {
  const turn = (ms = 50) => new Promise((done) => setTimeout(done, ms));
  const tools = (t) => document.querySelector(`table[data-table="${t}"]`).parentNode.querySelector(".table-tools");
  const links = [...document.querySelectorAll("#binary_cost .section-answer a")];
  if (links.length !== 1) return { links: links.length };
  links[0].click();
  await turn(600);
  const box = tools("by_binary");
  return { links: 1, named: links[0].textContent, hash: location.hash.split("~")[0],
           by_binary: [box.querySelector(".badge").textContent, box.querySelector("input.table-filter").value] };
})()"""


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
def test_the_cost_answer_reaches_its_binary_in_one_click(page):
    """The answer's one link is by_binary's leader; clicked, by_binary reads "1 matched" under `binary:<name>`."""
    from tools.bga_view import payloads

    run, uri = page
    top = payloads(str(run))["report.json"]["by_binary"][0]["binary"]
    with Browser(find_chrome()) as browser:
        got = {width: browser.measure(uri, _ANSWER, width, 900) for width in (1440, 390)}
    want = {"links": 1, "named": top, "hash": "#by_binary", "by_binary": ["1 matched", f"binary:{top}"]}
    assert got == {1440: want, 390: want}, got
