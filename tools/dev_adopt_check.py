#!/usr/bin/env python3
"""`UX-934`: an adopt job runs the guards that read its record before it pushes.

    python tools/dev_adopt_check.py tests/flake_ledger.json

A push made with `GITHUB_TOKEN` starts no workflow, so an adopt commit
is read by nothing until another branch's push gate inherits it. This
runs the guards that read each named record against the tree as it
stands and exits non-zero when one rejects it: the job goes red on the
run GitHub checks instead of pushing a commit it does not. A record no
guard is declared for is refused as well.
"""
import argparse
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]

#: The guards whose assertions read the committed record itself, not a
#: fixture - what a bad adopt of that record turns red.
GUARDS = {
    "tests/flake_ledger.json": (
        "tests/unit/test_a_file_with_three_excursions_has_a_filed_task.py",),
    "tests/ci_reference.json": (
        "tests/unit/test_a_slow_file_says_which_file.py",
        "tests/unit/test_the_process_documents_derive_their_figures.py"),
    "tests/touch_map.json": (
        "tests/unit/test_the_touching_map_is_measured.py",
        "tests/unit/test_the_loop_stays_fast.py"),
}


def guards(records):
    """The guard files for `records`, in order; `KeyError` names an undeclared one."""
    unknown = [record for record in records if record not in GUARDS]
    if unknown:
        raise KeyError(unknown)
    return sorted({guard for record in records for guard in GUARDS[record]})


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="run the guards that read each adopted record (UX-934)")
    parser.add_argument("records", nargs="+",
                        help="the repository-relative records this job adopted")
    args = parser.parse_args(argv)
    try:
        files = guards(args.records)
    except KeyError as error:
        print(f"::error::no guard is declared for {', '.join(error.args[0])} "
              f"in tools/dev_adopt_check.py - nothing was pushed (UX-934)")
        return 2
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         *files], cwd=REPO, check=False)
    if result.returncode:
        print(f"::error::a guard that reads {', '.join(args.records)} is red "
              f"on the adopted tree - nothing was pushed (UX-934). The "
              f"failure above names what to fix; re-run this job after it lands.")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
