"""UX-391: `wall_clock_share_us` showed the reader a composite key.

```text
codegen.bst|BUILD|BUILD|0    2.3 s
```

The task uid - element, kind, phase, attempt - printed verbatim as a row
label. A reader who types `codegen.bst` into the jump box does not match
it, and a reader who reads it has to know the tool's own key format to
see that three of the four fields are `BUILD`, `BUILD`, `0`.

`UX-374` swept the sections that renamed the reader's elements and left
this one, because its rule - **a published key renders as it was
published** - is right for an element uid and a binary name, and this is
the one class of published key that is a *composite*.

The composite is right as an identity: a retry and a fetch of one
element are different rows, and collapsing them would lose that. So it
stays, as the row's `data-key`; what changes is only what is shown.

Declared, not sniffed. `bga:keyed_by: "task_uid"` on the map says what
its keys are - the page cannot tell `a.bst|BUILD|BUILD|0` from a binary
called that without being told, and a viewer that guessed would be the
name-sniffing `UX-201` removed.
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import schemas                                       # noqa: E402
from tests import pages                                       # noqa: E402
from tests.browser import NO_BROWSER, Browser, find_chrome     # noqa: E402

node = __import__("shutil").which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is required")

_SPLIT = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null };
const fmt = await import("./bga/viewer/format.js");
console.log = (...a) => process.stdout.write(a.join(" ") + "\\n");
console.log(JSON.stringify({
  plain: fmt.taskUid("codegen.bst|BUILD|BUILD|0"),
  retried: fmt.taskUid("codegen.bst|BUILD|BUILD|2"),
  fetch: fmt.taskUid("extra.bst|FETCH|FETCH|0"),
  phased: fmt.taskUid("a.bst|BUILD|ASSEMBLE|0"),
  notAUid: fmt.taskUid("cc1plus"),
}));
"""


@pytest.fixture(scope="module")
def split():
    done = subprocess.run(
        [node, "--input-type=module", "-e", _SPLIT],
        capture_output=True, text=True, cwd=REPO, timeout=60,
        env=dict(os.environ, BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs")))
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


class TestTheContractSaysWhatTheKeysAre:
    def test_the_map_declares_its_key_kind(self):
        node = schemas.schema(schemas.ANALYZE)["properties"]["wall_clock_share_us"]
        assert node.get(schemas.KEYED_BY) == schemas.KEYED_BY_TASK_UID, (
            "the page cannot tell a task uid from a binary name without "
            "being told; a viewer that guessed would be the name-sniffing "
            "UX-201 removed")


@needs_node
class TestTheSplit:
    def test_the_element_is_the_label(self, split):
        assert split["plain"]["element"] == "codegen.bst"

    def test_the_qualifier_says_only_what_is_not_obvious(self, split):
        """`BUILD|BUILD|0` is one BUILD task, first attempt.

        Printing all three fields tells the reader nothing they did not
        have and puts the composite back on screen in words.
        """
        assert split["plain"]["qualifier"] == "BUILD", split["plain"]
        assert split["fetch"]["qualifier"] == "FETCH", split["fetch"]

    def test_a_retry_and_a_phase_are_said(self, split):
        """The two facts the composite carries that a name does not."""
        assert "attempt 2" in split["retried"]["qualifier"], split["retried"]
        assert "ASSEMBLE" in split["phased"]["qualifier"], split["phased"]

    def test_a_key_that_is_not_a_uid_is_left_alone(self, split):
        assert split["notAUid"] == {"element": "cc1plus", "qualifier": None}


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestOnTheRealPage:
    """The clause `UX-374` would have caught this with, one section over."""

    def test_no_rendered_label_is_a_composite_uid(self, tmp_path_factory):
        look = """(() => {
          const s = document.querySelector(
            'section[data-section="wall_clock_share_us"]');
          if (!s) return { found: false };
          const terms = [...s.querySelectorAll("dt")];
          return {
            found: true,
            rows: terms.length,
            composites: terms.filter(
              (t) => (t.textContent || "").includes("|")).length,
            keys: terms.map((t) => t.getAttribute("data-key")),
            firstLabel: (terms[0].textContent || "").trim(),
          };
        })()"""
        into = tmp_path_factory.mktemp("task-uid")
        uri = pages.export_uri(pages.FIXTURES["macro_micro"], into)
        with Browser(find_chrome()) as browser:
            seen = browser.measure(uri, look, 1440, 900)

        assert seen["found"], "the fixture no longer renders the section"
        assert seen["rows"] > 1, seen
        assert seen["composites"] == 0, (
            f"{seen['composites']} of {seen['rows']} labels still show the "
            f"pipe-delimited uid")
        assert all("|" in key for key in seen["keys"]), (
            "the composite must survive as the row's identity - a retry "
            "and a fetch of one element are different rows")
        assert seen["firstLabel"].startswith("codegen.bst"), seen["firstLabel"]
