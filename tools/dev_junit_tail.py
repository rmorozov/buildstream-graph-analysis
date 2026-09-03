#!/usr/bin/env python3
"""`UX-554`: name the failing tests when the log tail cannot.

`UX-491` made the drift gate's verdict reach a reader who only sees the
end of a CI log. That worked on the path where the gate runs — which is
the path where the suite *passed*. On a failure the later steps are
skipped, the junit is discarded with the runner, and the assertion has
long scrolled out of the log window an API will return.

So this prints, last, what a truncated log still needs: how many failed
and which, most legible first. It reads the junit rather than pytest's
stdout because that is the artifact that survives.

`UX-589`: with a second line saying whose junit it read - its own
totals and its age - because a reader who doubts the names has no
other way to match them against the suite's summary line above.
"""
import os
import sys
import time
import xml.etree.ElementTree as ET


def failures(path):
    """`(classname::name, kind, first line of the message)` per failure."""
    root = ET.parse(path).getroot()
    cases = root.iter("testcase")
    out = []
    for case in cases:
        for kind in ("failure", "error"):
            node = case.find(kind)
            if node is None:
                continue
            message = (node.get("message") or "").strip().splitlines()
            where = "::".join(x for x in (case.get("classname"),
                                          case.get("name")) if x)
            out.append((where, kind, message[0] if message else ""))
    return out


def totals(path):
    """`tests/failures/errors` as the junit records them, and its age."""
    root = ET.parse(path).getroot()
    counted = {key: 0 for key in ("tests", "failures", "errors")}
    for suite in root.iter("testsuite"):
        for key in counted:
            counted[key] += int(suite.get(key) or 0)
    return counted, time.time() - os.path.getmtime(path)


def _age(seconds):
    if seconds < 120:
        return f"{seconds:.0f}s"
    if seconds < 7200:
        return f"{seconds / 60:.0f}m"
    return f"{seconds / 3600:.1f}h"


def provenance(path):
    """The line that says whose junit this is (`UX-589`)."""
    counted, old = totals(path)
    return (f"  read from {path}: {counted['tests']} test(s) recorded, "
            f"{counted['failures']} failure(s), {counted['errors']} "
            f"error(s), written {_age(old)} before this read - match that "
            f"against the suite's own summary line above")


def main(argv):
    if len(argv) != 2:
        print("usage: dev_junit_tail.py <junit.xml>", file=sys.stderr)
        return 2
    try:
        found = failures(argv[1])
    except (OSError, ET.ParseError) as exc:
        # Never mask the real failure with one of its own.
        print(f"the junit could not be read ({exc}); the suite's own "
              f"output above is all there is", file=sys.stderr)
        return 0
    if not found:
        print("the junit records no failure - the suite failed elsewhere "
              "(collection, a plugin, or the make target itself)")
    else:
        print(f"{len(found)} test(s) failed, named here because the log "
              f"tail above may be truncated (UX-554):")
        for where, kind, message in found:
            print(f"  {kind.upper():7s} {where}")
            if message:
                print(f"          {message[:160]}")
    print(provenance(argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
