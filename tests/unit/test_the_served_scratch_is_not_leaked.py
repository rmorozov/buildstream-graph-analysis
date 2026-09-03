"""UX-559: `bga view --serve` left one scratch directory behind per run.

The served timeline is rendered into `tempfile.mkdtemp(prefix="bga-serve-")`,
held as class state on the handler, and nothing removed it — so a
long-lived viewer leaked a directory per served run until something else
emptied `/tmp`. `UX-546`'s track counted 2,799 of them on a box that had
only ever run the suite; this working copy held 102 when the item was
picked up.

The scratch's life is the server's, so `server_close()` is where it goes:
`serve()`'s contract is already "the caller closes it", which makes every
route out — the serve loop's `finally` and the `--perfetto` refusal that
never enters it — clean up on a call it already makes.

**The count is the instrument, not the name.** The guard asks how many
`bga-serve-*` directories exist before, during and after, and the middle
reading is what stops it being vacuous: a test that only checked "none
afterwards" would pass just as well against a server that never rendered
a trace at all.

`tempfile.tempdir` is pointed at the test's own directory so the reading
is this test's and not the machine's — under `-n auto` another worker
serving a run would otherwise land in the same count.
"""
import glob
import os
import pathlib
import sys
import tempfile
import threading
import urllib.request

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages                                       # noqa: E402
from tools import bga_view                                    # noqa: E402

#: The prefix the module mkdtemps with. Read from nothing - if it is
#: reworded this guard should keep counting the directories the module
#: actually makes, which is why the *count* is the assertion.
PREFIX = "bga-serve-*"


@pytest.fixture
def isolated_tmp(tmp_path, monkeypatch):
    """`mkdtemp` with no `dir=` lands here, so the count is ours."""
    scratch = tmp_path / "tmp"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    return scratch


def _scratches(where):
    return len(glob.glob(os.path.join(str(where), PREFIX)))


def _serve_once(run, where):
    """Serve `run`, fetch its timeline, stop. The count while it lived."""
    httpd, url = bga_view.serve(str(run))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        body = urllib.request.urlopen(
            url + bga_view.TRACE_NAME, timeout=30).read()
        assert body, "the timeline endpoint served nothing, so no scratch " \
                     "was ever made and this guard would be vacuous"
        during = _scratches(where)
    finally:
        httpd.shutdown()
        httpd.server_close()
    return during


class TestTheServedScratchIsNotLeaked:

    def test_serving_twice_and_stopping_leaves_nothing(self, tmp_path,
                                                       isolated_tmp):
        """The acceptance test: count before, count after, and the two
        agree across two served runs."""
        run = pages.two_plane_snapshot(tmp_path / "store")
        before = _scratches(isolated_tmp)
        for _ in range(2):
            _serve_once(run, isolated_tmp)
        after = _scratches(isolated_tmp)
        assert after == before, (
            f"serving twice left {after - before} scratch director(y/ies) "
            f"behind - the leak UX-559 was filed on")

    def test_the_scratch_exists_while_the_server_does(self, tmp_path,
                                                      isolated_tmp):
        """The positive control. Without this, a server that rendered no
        trace would satisfy the clause above by doing nothing."""
        run = pages.two_plane_snapshot(tmp_path / "store")
        before = _scratches(isolated_tmp)
        during = _serve_once(run, isolated_tmp)
        assert during == before + 1, (
            f"a served timeline made no scratch directory ({before} -> "
            f"{during}), so the clause above is not measuring a cleanup")
        assert _scratches(isolated_tmp) == before

    def test_closing_without_serving_a_trace_is_fine(self, tmp_path,
                                                     isolated_tmp):
        """The route out that never renders one: `server_close` must not
        care that there is nothing to remove."""
        run = pages.two_plane_snapshot(tmp_path / "store")
        httpd, _ = bga_view.serve(str(run))
        httpd.server_close()
        assert _scratches(isolated_tmp) == 0
        assert httpd.RequestHandlerClass.trace_scratch is None
