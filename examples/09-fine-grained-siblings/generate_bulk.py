#!/usr/bin/env python3
"""Generate `files/bulk/` - the staged tree whose *file count* is its cost.

`UX-120` needed a project where the sandbox toll is measurable, and the
obstacle was not the idea but BuildStream's own instrumentation:
dependencies are staged by hardlink and the phases are timed to the
second, so a real 8k-file C++ sysroot stages in `00:00:00` and its toll
rounds to zero. That is why `UX-100`'s merge criterion had never fired on
a real capture - not because no project is too fine-grained, but because
the measurement cannot see a sub-second staging.

Measured on this fixture: 8k files stage in under a second (toll 0.0s,
share 0.00); 60k files stage in one (toll 1.0s, share 0.50), which clears
both halves of the criterion. So 60k is not a round number, it is the
point at which BuildStream's second-resolution timing can report the
thing being measured.

One byte per file, so the tree is inodes rather than megabytes and the
CAS deduplicates the content to a single blob.
"""
import os
import sys

DIRS = 60
PER_DIR = 1000


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "files", "bulk", "usr", "share",
    )
    for directory in range(DIRS):
        path = os.path.join(root, f"d{directory:03d}")
        os.makedirs(path, exist_ok=True)
        for index in range(PER_DIR):
            with open(os.path.join(path, f"f{index:04d}.dat"), "w") as handle:
                handle.write("x")
    print(f"Generated {DIRS * PER_DIR} files under {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
