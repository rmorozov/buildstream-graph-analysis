#!/usr/bin/env python3
"""`UX-997`: CI's measured records live on `refs/heads/records`, not main.

    python tools/dev_records.py fetch [--at SHA]
    python tools/dev_records.py publish

`fetch` writes the four record paths (`tests/ci_reference.json`,
`tests/touch_map.json`, `tests/flake_ledger.json`,
`docs/audits/mutation.md`) from that branch's tip, or `--at` a named
sha - the branch is append-only, so every past sha stays reachable.
Offline, a previous fetch's copy on disk is reused, printed
`<sha> (cached)`. `fetch` also records, in `git config --local`, the tip
it confirmed the tree now reflects - `publish` refuses (writing
nothing) unless that still matches the tip current *now*, so a `fetch`
that failed silently cannot make `publish` overlay this run's delta
onto a tip it never actually read, dropping rows published since
(`UX-997`). `publish` runs `dev_adopt_check` on whichever paths the
tree carries dirty, builds one commit on the records tip (or seeds an
orphan root from the tree's own copies, the first time), and pushes it
there - never to main, and never force. T1 (`UX-997`): the four paths
stay tracked on main too; T2 moves them off it.
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import dev_adopt_check

REPO = pathlib.Path(__file__).resolve().parents[1]
#: `UX-781`'s own reason: a bare command name is `ruff` S607, a full
#: path is not.
GIT = shutil.which("git") or "git"
RECORDS_REF = "refs/heads/records"
SHA_MARKER = REPO / "tests" / ".records-sha"
RECORD_PATHS = ("tests/ci_reference.json", "tests/touch_map.json",
                "tests/flake_ledger.json", "docs/audits/mutation.md")
#: `git config --local`, scoped to this checkout: the tip `fetch` last
#: confirmed the tree reflects, for `publish` to check itself against
#: before it overlays onto whatever tip is current *now*.
BASE_KEY = "bga.records-base"
BOT_ENV = {"GIT_AUTHOR_NAME": "github-actions[bot]",
           "GIT_COMMITTER_NAME": "github-actions[bot]",
           "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
           "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com"}


def _git(*args, env=None, check=False):
    return subprocess.run([GIT, *args], cwd=REPO, env=env,
                          capture_output=True, text=True, check=check)


def _cached_sha():
    return SHA_MARKER.read_text(encoding="utf-8").strip() if SHA_MARKER.is_file() else None


def _set_base(value):
    _git("config", "--local", BASE_KEY, value, check=True)


def _get_base():
    """The recorded base, `None` if `fetch` never confirmed one (never
    ran, or failed to reach the remote at all)."""
    got = _git("config", "--get", BASE_KEY)
    return got.stdout.strip() if got.returncode == 0 else None


def fetch(argv=None):
    parser = argparse.ArgumentParser(description="read the records branch")
    parser.add_argument("--at", help="a sha the branch's history reaches")
    args = parser.parse_args(argv)
    fetched = _git("fetch", "--quiet", "origin", RECORDS_REF)
    if fetched.returncode == 0:
        sha = args.at or _git("rev-parse", "FETCH_HEAD", check=True).stdout.strip()
        if _git("cat-file", "-e", f"{sha}^{{commit}}").returncode == 0:
            written = []
            for path in RECORD_PATHS:
                shown = _git("show", f"{sha}:{path}")
                if shown.returncode == 0:
                    (REPO / path).parent.mkdir(parents=True, exist_ok=True)
                    (REPO / path).write_text(shown.stdout, encoding="utf-8")
                    written.append(path)
            # Staged, not committed: `publish`'s dirty check then reads
            # against *this* baseline rather than main's frozen commit,
            # so a run that adopts nothing new sees nothing dirty.
            if written:
                _git("add", "--", *written)
            SHA_MARKER.write_text(sha + "\n", encoding="utf-8")
            _set_base(sha)
            print(f"records @ {sha}")
            return 0
    elif "couldn't find remote ref" in fetched.stderr:
        # Reached the remote; confirmed there is no branch yet - a
        # known, not an unknown, base.
        _set_base("none")
        print("records @ none")
        return 0
    cached = _cached_sha()
    if cached is None:
        print("::error::no records reachable, and no cached copy "
              "(tools/dev_records.py fetch)")
        return 1
    print(f"{cached} (cached)")
    return 0


def _dirty(path):
    """Working tree against the index, not `HEAD` - `fetch` stages the
    records baseline there, so a run that adopted nothing sees nothing
    dirty even though `main`'s own committed copy is long stale."""
    return _git("diff", "--quiet", "--", path).returncode != 0


def _records_tip():
    return (_git("rev-parse", "FETCH_HEAD", check=True).stdout.strip()
            if _git("fetch", "--quiet", "origin", RECORDS_REF).returncode == 0 else None)


def publish(argv=None):
    argparse.ArgumentParser(description="push the records this run changed").parse_args(argv)
    changed = [path for path in RECORD_PATHS if _dirty(path)]
    if not changed:
        print("nothing to publish - no record changed")
        return 0
    # `changed` only means anything relative to the tip `fetch` last
    # confirmed: overlay it onto a *different*, newer tip and whatever
    # that tip gained since goes missing from the commit built here
    # (`UX-997`, the verifier's repro). `concurrency: records` already
    # serialises every publisher, so a mismatch here is a fetch that
    # failed silently, not a race to retry.
    base = _get_base()
    tip = _records_tip()
    base_known = None if base in (None, "none") else base
    if base_known is None and tip is None:
        seeding = True
    elif base_known is not None and base_known == tip:
        seeding = False
    else:
        print(f"::error::the records branch moved since this run last read "
              f"it (read {base or 'none'}, now {tip or 'none'}) - nothing "
              f"was published (UX-997)")
        return 1
    guarded = [path for path in changed if path in dev_adopt_check.GUARDS]
    if guarded and (code := dev_adopt_check.main(guarded)):
        return code
    paths = [p for p in (RECORD_PATHS if seeding else changed) if (REPO / p).is_file()]
    scratch = tempfile.mkdtemp(prefix="dev-records-index-")
    index_env = {**os.environ, "GIT_INDEX_FILE": str(pathlib.Path(scratch) / "index")}
    try:
        if not seeding:
            _git("read-tree", tip, env=index_env, check=True)
        for path in paths:
            blob = _git("hash-object", "-w", "--", path, env=index_env, check=True).stdout.strip()
            _git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}",
                 env=index_env, check=True)
        tree = _git("write-tree", env=index_env, check=True).stdout.strip()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    parents = [] if seeding else ["-p", tip]
    commit_env = {**os.environ, **BOT_ENV}
    commit = _git("commit-tree", tree, *parents, "-m",
                  f"records: {', '.join(changed)}", env=commit_env,
                  check=True).stdout.strip()
    pushed = _git("push", "origin", f"{commit}:{RECORDS_REF}")
    if pushed.returncode:
        print(f"::warning::the records branch refused the update; "
              f"re-run to retry\n{pushed.stderr}")
        return pushed.returncode
    print(f"records @ {commit}")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in ("fetch", "publish"):
        print("usage: dev_records.py {fetch,publish} ...", file=sys.stderr)
        return 2
    return {"fetch": fetch, "publish": publish}[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main())
