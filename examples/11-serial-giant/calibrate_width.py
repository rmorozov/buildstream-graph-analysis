#!/usr/bin/env python3
"""UX-1004: how much parallelism the runner behind the sandboxes has.

Builds `giant.bst` alone at each `max-jobs` width (its artifact deleted
between builds, the toolchain cached) and prints `effective = t(1)/t(w)`
per width and the knee: the widest width whose step from the previous
one still cut the wall by `GAIN`. The pool's ceiling is judged against
that, not `nproc`.

    python3 calibrate_width.py <project> 1 2 4 6 8
"""
import os
import subprocess
import sys
import tempfile
import time

#: A wider width that saves less than this is not paying for itself.
GAIN = 0.05


def effective(walls: dict) -> dict:
    """`{width: t(1)/t(width)}`; needs width 1."""
    return {w: walls[1] / t for w, t in sorted(walls.items())}


def knee(walls: dict, gain: float = GAIN) -> int:
    """The widest width reached while each step still cut the wall by `gain`."""
    widths = sorted(walls)
    best = widths[0]
    for prev, cur in zip(widths, widths[1:]):
        if walls[cur] > walls[prev] * (1 - gain):
            break
        best = cur
    return best


def build_at(project: str, width: int, run=subprocess.run) -> float:
    """Seconds for `bst build giant.bst` at `max-jobs: width`, giant rebuilt."""
    with tempfile.TemporaryDirectory() as xdg:
        with open(os.path.join(xdg, "buildstream2.conf"), "w", encoding="utf-8") as conf:
            conf.write(f"cache:\n  quota: 3G\n  reserved-disk-space: 500M\n"
                       f"build:\n  max-jobs: {width}\n")
        env = dict(os.environ, XDG_CONFIG_HOME=xdg)
        run(["bst", "artifact", "delete", "giant.bst"], cwd=project, env=env, check=False)
        start = time.monotonic()
        run(["bst", "build", "giant.bst"], cwd=project, env=env, check=True)
        return time.monotonic() - start


def render(walls: dict) -> list:
    eff = effective(walls)
    lines = [f"width {w}: {walls[w]:.2f}s  effective {eff[w]:.2f}" for w in sorted(walls)]
    lines.append(f"knee: width {knee(walls)} (every step up to it cut the wall by >= {GAIN:.0%})")
    return lines


def main(argv=None, run=subprocess.run) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2 or "1" not in args[1:]:
        print("usage: calibrate_width.py PROJECT 1 W2 W3 ...", file=sys.stderr)
        return 2
    project, widths = args[0], sorted({int(w) for w in args[1:]})
    run(["bst", "build", "toolchain.bst"], cwd=project, check=True)
    walls = {w: build_at(project, w, run) for w in widths}
    print("\n".join(render(walls)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
