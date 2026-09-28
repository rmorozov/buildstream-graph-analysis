"""UX-1079: the opens pass re-opened the raw log with plain `open`,
after the process pass had already gone through `_open_maybe_gzipped`
(`UX-330`). Every snapshot stores its Plane 2 log as `plane2.log.gz`,
so on a real capture the second pass read deflate bytes and silently
found no `OPENS` block at all.
"""
import gzip

from tools.bst_native_build_tracer import load_and_summarize

_LOG = (
    "START pid=2 ppid=1 ts=1.0 element=a.bst cmd=cc1\n"
    "OPENS pid=2 element=a.bst unique=2 dropped=0\n"
    "/usr/include/foo.h\n"
    "/usr/include/bar.h\n"
    "END pid=2 ppid=1 ts=2.0 element=a.bst cmd=cc1\n"
)


def test_opens_captured_is_the_same_plain_or_gzipped(tmp_path):
    plain = tmp_path / "trace.log"
    plain.write_text(_LOG)
    gzipped = tmp_path / "trace.log.gz"
    with gzip.open(gzipped, "wt") as handle:
        handle.write(_LOG)

    plain_report = load_and_summarize(str(plain))
    gz_report = load_and_summarize(str(gzipped))

    assert gz_report["opens_captured"] == plain_report["opens_captured"]
    assert gz_report["opens_captured"] == {
        "a.bst": {"paths": 2, "dropped": 0, "processes": 1,
                  "windows": 1, "relative": 0, "dirfd": 0},
    }
