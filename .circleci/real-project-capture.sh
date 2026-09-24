#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"
export PATH="$HOME/.local/bin:$PATH"
mkdir -p capture
finish() {
  rc=$?
  trap - EXIT
  set +e
  if [ -f capture/build.log ]; then
    python3 -m tools.bst_extract_run fdsdk capture/build.log capture/run --format wrapped --native-max-jobs "$MAX_JOBS"
  fi
  if [ -d capture/run ]; then
    bga analyze -d capture/run > capture/analyze.txt 2>&1
    bga analyze -d capture/run -f json > capture/analyze.json 2> capture/analyze-error.txt
    if [ -f capture/native-report.json ]; then
      bga correlate capture/run capture/native-report.json > capture/correlate.txt 2>&1
    fi
  fi
  if [ -d "$HOME/.cache/buildstream/logs" ]; then
    tar -czf capture/bst-element-logs.tar.gz -C "$HOME/.cache/buildstream/logs" --exclude=_casd .
  fi
  {
    echo "fdsdk_ref=$(git -C fdsdk rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "bga_ref=$(git rev-parse HEAD)"
    echo "bst_version=$(bst --version 2>/dev/null || echo unknown)"
    echo "runner_os=$(uname -a)"
    echo "nproc=$(nproc)"
    python3 -c 'from tools.bga_snapshot import cpu_topology; print(cpu_topology())'
    echo "builders=$BUILDERS"
    echo "max_jobs=$MAX_JOBS"
    echo "trace_opens=$TRACE_OPENS"
    echo "trace_spine=$TRACE_SPINE"
    echo "capture_mode=$CAPTURE_MODE"
    echo "jobserver=$JOBSERVER"
    echo "target=$TARGET"
    echo "mem_total_kb=$(awk '/MemTotal/{print $2}' /proc/meminfo)"
    df -h /
  } > capture/capture-context.txt
  # CircleCI stores capture/ even when the build fails. Preserve the build exit status.
  exit "$rc"
}
trap finish EXIT
: "${FDSDK_REF:?set FDSDK_REF in CircleCI pipeline parameters}"
: "${TARGET:?set TARGET in CircleCI pipeline parameters}"
: "${BUILDERS:?set BUILDERS in CircleCI pipeline parameters}"
: "${MAX_JOBS:?set MAX_JOBS in CircleCI pipeline parameters}"
: "${TRACE_OPENS:?set TRACE_OPENS in CircleCI pipeline parameters}"
: "${TRACE_SPINE:?set TRACE_SPINE in CircleCI pipeline parameters}"
: "${CAPTURE_MODE:?set CAPTURE_MODE in CircleCI pipeline parameters}"
: "${JOBSERVER:?set JOBSERVER in CircleCI pipeline parameters}"
case "$CAPTURE_MODE" in incremental|cold) ;; *) echo "invalid capture mode" >&2; exit 2 ;; esac
case "$JOBSERVER" in off|auto) ;; *) echo "invalid jobserver mode" >&2; exit 2 ;; esac
case "$TRACE_OPENS:$TRACE_SPINE" in true:true|true:false|false:true|false:false) ;; *) exit 2 ;; esac
[[ "$BUILDERS" =~ ^[1-9][0-9]*$ && "$MAX_JOBS" =~ ^[1-9][0-9]*$ ]] || exit 2
# Use an isolated Python environment on the CircleCI VM.
sudo apt-get update
sudo apt-get install -y bubblewrap lzip python3-venv
python3 -m venv /tmp/bga-capture-venv
export PATH="/tmp/bga-capture-venv/bin:$PATH"

# Make the sandbox usable, and prove it before spending an hour
sysctl kernel.apparmor_restrict_unprivileged_userns || true
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0 || true
bwrap --unshare-net --unshare-pid --ro-bind / / --dev /dev /bin/true
echo "bwrap --unshare-net works"

# Install BuildStream and bga
pip install -e ".[dev]"
# Pinned so a runner image cannot move it (`UX-939`). Captures
# already in this repository were taken on 2.7.0; a capture taken
# after this line moved is on 2.8.1, and `run_context` records
# which. dulwich/requests are freedesktop-sdk's own plugin
# dependencies (git and docker sources).
pip install 'BuildStream==2.8.1' 'buildstream-plugins==2.8.0' dulwich requests
bst --version

# Clone freedesktop-sdk
mkdir -p fdsdk
git -C fdsdk init -q
git -C fdsdk remote add origin https://gitlab.com/freedesktop-sdk/freedesktop-sdk.git
git -C fdsdk fetch -q --depth 1 origin "$FDSDK_REF"
git -C fdsdk checkout -q FETCH_HEAD
git -C fdsdk rev-parse HEAD

# Check the capture environment against a real project
mkdir -p capture
set +e
bga doctor fdsdk | tee capture/doctor.txt
# Captured into a variable on the very next line, because
# PIPESTATUS is rewritten by every command after it - including
# the `echo` that reports it. `$?` alone would be `tee`'s, which
# is the trap UX-97 recorded.
rc=${PIPESTATUS[0]}
set -e
echo "doctor_exit=$rc" > capture/doctor-outcome.txt
echo "doctor exited $rc"

# Extract the declared graph
if [ "$CAPTURE_MODE" = incremental ]; then
mkdir -p capture
python3 -m tools.bst_show_to_graph fdsdk "$TARGET" capture/graph-declared.json
fi

# Compute the rebuild set
python3 -m tools.bst_rebuild_set capture/graph-declared.json \
  --cut components/_private/python3-flit-core.bst \
  --cut components/openssl.bst \
  --cut components/expat.bst \
  --cut components/bison.bst \
  --cut components/icu.bst \
  --cut components/doxygen.bst \
  --cut components/which.bst \
  --cut components/ninja.bst \
  --cut "$TARGET" \
  | tee capture/rebuild-set.txt
wc -l < capture/rebuild-set.txt

# Warm the local cache from the project's remote cache
if [ "$CAPTURE_MODE" = incremental ]; then
cd fdsdk
bst --no-interactive artifact pull --deps all "$TARGET"
bst --no-interactive show --deps all --format '%{name}|%{state}' "$TARGET" \
  > ../capture/state-after-warm.txt
echo "cached after warm: $(grep -c '|cached$' ../capture/state-after-warm.txt) / $(wc -l < ../capture/state-after-warm.txt)"
fi

# Delete the rebuild set and pre-fetch its sources
if [ "$CAPTURE_MODE" = incremental ]; then
cd fdsdk
xargs -a ../capture/rebuild-set.txt \
  bst --no-interactive artifact delete
# Only the deleted elements need sources: everything else is
# still cached and will never be built.
xargs -a ../capture/rebuild-set.txt \
  bst --no-interactive source fetch --deps none
bst --no-interactive show --deps all --format '%{name}|%{state}' "$TARGET" \
  > ../capture/state-after-delete.txt
fi

# Pre-fetch every source in the closure (cold mode)
if [ "$CAPTURE_MODE" = cold ]; then
cd fdsdk
bst --no-interactive source fetch --deps all "$TARGET"
bst --no-interactive show --deps all --format '%{name}|%{state}' "$TARGET" \
  > ../capture/state-after-delete.txt
cached=$(grep -c '|cached$' ../capture/state-after-delete.txt || true)
total=$(wc -l < ../capture/state-after-delete.txt)
echo "cold start: $cached of $total elements cached (expected 0)"
if [ "$cached" != "0" ]; then
  echo "a cold capture with cached elements is not a cold capture" >&2
  exit 1
fi
fi

# Verify the cut is exactly the rebuild set
if [ "$CAPTURE_MODE" = incremental ]; then
python3 - <<'EOF'
from pathlib import Path

wanted = set(Path("capture/rebuild-set.txt").read_text().split())
states = {}
for line in Path("capture/state-after-delete.txt").read_text().splitlines():
    if "|" in line:
        name, _, state = line.rpartition("|")
        states[name] = state

# `junction` elements are not artifacts and are never cached.
not_built = {n for n, s in states.items() if s not in ("cached", "junction")}

unexpected = sorted(not_built - wanted)
already_cached = sorted(wanted - not_built)
print(f"{len(states)} elements, {len(not_built)} not cached, "
      f"{len(wanted)} in the rebuild set")
if already_cached:
    print("still cached despite being deleted: " + ", ".join(already_cached))
if unexpected:
    print("NOT cached and NOT in the rebuild set:")
    for name in unexpected:
        print(f"  {name} ({states[name]})")
    raise SystemExit(
        f"{len(unexpected)} element(s) would be built beyond the "
        "intended cut - the warm phase did not pull the whole closure"
    )
EOF
fi

# Capture the build (both planes)
OPENS=""
if [ "$TRACE_OPENS" = "true" ]; then OPENS="--trace-opens"; fi
SPINE=""
if [ "$TRACE_SPINE" = "true" ]; then SPINE="--trace-spine"; fi
JS=""
if [ "$JOBSERVER" = "auto" ]; then JS="--jobserver $(nproc)"; fi
# UX-905: a hang leaves no report, so a quiet host is dumped as it happens.
python3 -m tools.hang_witness --out capture/hang-witness.log &
WITNESS=$!
set +e
python3 -m tools.bst_native_build_tracer run \
  --wrapped-log capture/build.log \
  --raw-log capture/native-trace.log \
  --invocation-log capture/invocations.jsonl \
  --argv-log capture/bwrap-argv.jsonl \
  $OPENS $SPINE $JS \
  fdsdk capture/native-report.json \
  -- bst --no-interactive --builders "$BUILDERS" --max-jobs "$MAX_JOBS" \
       build --ignore-project-artifact-remotes \
             --ignore-project-source-remotes "$TARGET"
traced_rc=$?
kill "$WITNESS" 2>/dev/null
echo "traced build exit: $traced_rc"
echo "traced_build_exit=$traced_rc" > capture/capture-outcome.txt
final_rc=$traced_rc
if [ "$traced_rc" -ne 0 ]; then
  mv capture/build.log capture/build-traced.log
  # A failed build leaves a *failed* artifact cached, so the
  # retry needs --retry-failed or BuildStream skips straight
  # past the elements that just failed.
  python3 -m tools.bst_run_wrapped fdsdk capture/build.log \
    -- bst --no-interactive --builders "$BUILDERS" --max-jobs "$MAX_JOBS" \
         build --retry-failed \
               --ignore-project-artifact-remotes \
               --ignore-project-source-remotes "$TARGET"
  plain_rc=$?
  echo "plain build exit: $plain_rc"
  echo "plain_build_exit=$plain_rc" >> capture/capture-outcome.txt
  final_rc=$plain_rc
  # UX-66: from here the two planes describe DIFFERENT builds -
  # `run/` will be extracted from this plain build's log, while
  # native-report.json came from the traced one. `bga correlate`
  # joins Plane 2 sandboxes against Plane 1 BUILD spans, so
  # leaving both in place would silently match one build's
  # sandboxes to another build's timeline. Keep the Plane 2
  # report under a name nothing joins on, and say so.
  if [ -f capture/native-report.json ]; then
    mv capture/native-report.json capture/native-report-traced-only.json
  fi
  echo "planes_describe_different_builds=1" >> capture/capture-outcome.txt
fi
set -e
# Only a build that failed *both* ways stops the job; a Plane 1
# capture on its own is still a usable result.
exit "$final_rc"
