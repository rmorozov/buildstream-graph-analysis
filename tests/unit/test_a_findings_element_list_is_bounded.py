"""UX-1053 (styleguide §3k, element list): a finding card's `elements`.

`shared-source-blast` drew one link per element it names: 11, 172 and
572 links on the 74-, 1,202- and 4,002-element two-plane pages, +930
and +3,255 px landed. Past `TABLE_OPENS_BOUNDED_ABOVE` the list is §1's
bounded list, as `app.js`'s `bounded` does for the element sections.
This is `renderFindings` in the shim; the page-level half is
`test_the_page_has_a_volume_budget.py` on `scale_both` and `xl_both`.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: Written here, not read from the constant it audits: raising the bound
#: past these reds the guard.
CARD_CONTROLS_CEILING = 45
SIZES = (11, 40, 41, 572, 4002)

_SCRIPT = r"""
globalThis._makeNode = (await import(process.env.BGA_DOM_SHIM)).makeNode;
const { installDocument } = await import(process.env.BGA_DOM_SHIM);
const document = installDocument();
const sections = await import(process.env.BGA_REPO + "/bga/viewer/sections.js");

const walk = (n, keep, out = []) => {
  if (keep(n)) out.push(n);
  for (const c of n.children ?? []) walk(c, keep, out);
  return out;
};
const CONTROLS = new Set(["a", "button", "input", "select"]);
const out = {};
for (const n of JSON.parse(process.env.SIZES)) {
  const elements = Array.from({ length: n }, (_, i) => `layer/mod${i}.bst`);
  const section = sections.renderFindings([{ id: "shared-source-blast",
    severity: "info", title: "t", elements }], null, undefined);
  document.body.append(section);
  const card = walk(section, (x) => x.tagName === "article")[0];
  const bounded = walk(card, (x) => x.getAttribute?.("data-bounded") === "list");
  out[n] = {
    controls: walk(card, (x) => CONTROLS.has(x.tagName)).length,
    links: walk(card, (x) => x.tagName === "a"
                && x.getAttribute("data-element")).length,
    items: bounded.length ? Number(bounded[0].getAttribute("data-items")) : null,
  };
}
process.stdout.write(JSON.stringify(out) + "\n");
"""


@pytest.fixture(scope="module")
def measured():
    result = subprocess.run(
        [node, "--input-type=module", "-e", _SCRIPT],
        capture_output=True, text=True, cwd=REPO, timeout=60,
        env=dict(os.environ, BGA_REPO=str(REPO), SIZES=json.dumps(SIZES),
                 BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs")))
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


@needs_node
class TestAFindingsElementListIsBounded:
    def test_under_the_bound_every_element_is_a_link(self, measured):
        for n in (11, 40):
            assert measured[str(n)]["links"] == n, measured

    def test_the_card_does_not_grow_with_the_run(self, measured):
        at = {n: measured[str(n)]["controls"] for n in (41, 572, 4002)}
        assert len(set(at.values())) == 1, at
        assert at[4002] <= CARD_CONTROLS_CEILING, at

    def test_past_the_bound_no_name_is_dropped(self, measured):
        for n in (41, 572, 4002):
            assert measured[str(n)]["items"] == n, measured
