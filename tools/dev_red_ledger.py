#!/usr/bin/env python3
"""UX-1125: which test files went red on a merged pull request.

    python tools/dev_red_ledger.py --from-pr SHA [--repo OWNER/NAME]

Finds the pull request that merged `SHA`, its red `ci.yml` runs, and
their `junit-*` artifacts through the REST API (`GITHUB_TOKEN`; no `gh`),
then appends `{file, sha, round}` to `tests/red_ledger.json` per failing
file. `dev_guard_prices` reads that ledger as each file's last catch.
Publishing it is `dev_records.py publish`. Every refusal exits 0.
"""

import argparse
import io
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
import zipfile

import defusedxml.ElementTree as ET

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import dev_tier_drift

LEDGER_PATH = "tests/red_ledger.json"
LEDGER = REPO / LEDGER_PATH
API = "https://api.github.com"


def failing_files(junit, file_of=dev_tier_drift.file_of):
    """The sorted test files with a failed or errored testcase in `junit` (a path or file object)."""
    files = set()
    for case in ET.parse(junit).iter("testcase"):
        if case.find("failure") is not None or case.find("error") is not None:
            name = file_of(case.get("classname") or "")
            if name:
                files.add(name)
    return sorted(files)


def append(ledger, files, sha, round_):
    """`ledger` plus one `{file, sha, round}` per file not already recorded for `sha`."""
    seen = {(entry["file"], entry["sha"]) for entry in ledger}
    return list(ledger) + [
        {"file": name, "sha": sha, "round": round_} for name in sorted(set(files)) if (name, sha) not in seen
    ]


def last_catch(ledger):
    """`{file: latest round}` over a ledger."""
    found = {}
    for entry in ledger:
        found[entry["file"]] = max(found.get(entry["file"], entry["round"]), entry["round"])
    return found


def _get(url, token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        return response.read()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _download(url, token):
    """An artifact zip: the API answers 302 to a pre-signed URL that must not see the token."""
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        return urllib.request.build_opener(_NoRedirect).open(request, timeout=60).read()
    except urllib.error.HTTPError as err:
        if err.code not in (301, 302, 303, 307, 308):
            raise
        return urllib.request.urlopen(err.headers["Location"], timeout=120).read()


def red_junits(repo, sha, token, get=_get, download=_download):
    """Junit bytes from the red `ci.yml` pull-request runs of the PR that merged `sha`."""
    pulls = json.loads(get(f"{API}/repos/{repo}/commits/{sha}/pulls", token))
    out = []
    for pull in pulls[:1]:
        query = f"head_sha={pull['head']['sha']}&event=pull_request&per_page=100"
        for run in json.loads(get(f"{API}/repos/{repo}/actions/runs?{query}", token))["workflow_runs"]:
            if run.get("path", "").endswith("ci.yml") and run.get("conclusion") == "failure":
                arts = json.loads(get(f"{API}/repos/{repo}/actions/runs/{run['id']}/artifacts?per_page=100", token))
                for art in arts["artifacts"]:
                    if art["name"].startswith("junit-") and not art.get("expired"):
                        with zipfile.ZipFile(io.BytesIO(download(art["archive_download_url"], token))) as archive:
                            out += [archive.read(n) for n in archive.namelist() if n.endswith(".xml")]
    return out


def main(argv=None):
    import dev_guard_prices  # it imports this module

    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--from-pr", required=True, metavar="SHA", help="the merge commit on main")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    args = parser.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN")
    if not token or not args.repo:
        print("no GITHUB_TOKEN or repository - nothing recorded")
        return 0
    try:
        junits = red_junits(args.repo, args.from_pr, token)
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as err:
        print(f"::warning::the red runs were unreachable - nothing recorded ({err})")
        return 0
    files = sorted({name for raw in junits for name in failing_files(io.BytesIO(raw))})
    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else []
    grown = append(ledger, files, args.from_pr, dev_guard_prices.current_round())
    if grown != ledger:
        LEDGER.write_text(json.dumps(grown, indent=1) + "\n", encoding="utf-8")
    print(f"{len(grown) - len(ledger)} red file(s) recorded for {args.from_pr[:8]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
