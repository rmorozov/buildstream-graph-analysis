"""UX-1384: `make lock-check` - is `requirements.lock` what the compile writes?

    python3 tools/dev_lock_check.py <compile command...>

Seeds a copy of the committed lock in a directory of this run's own,
runs the compile with `-o <copy>` appended, and compares; the directory
goes with the process, so two runs in one checkout never read each
other's output. Exit 1 names `make lock-sync`.
"""

import difflib
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]


def main(argv: list[str]) -> int:
    lock = REPO / "requirements.lock"
    with tempfile.TemporaryDirectory(prefix="bga-lock-check-") as scratch:
        copy = pathlib.Path(scratch) / "requirements.lock"
        shutil.copyfile(lock, copy)
        subprocess.run([*argv, "-o", str(copy)], cwd=REPO, check=True)
        if copy.read_bytes() == lock.read_bytes():
            return 0
        old, new = lock.read_text().splitlines(True), copy.read_text().splitlines(True)
        sys.stdout.writelines(difflib.unified_diff(old, new, "requirements.lock", "compiled"))
    print("requirements.lock is stale: run make lock-sync")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
