#!/usr/bin/env bash
# Stages a *dynamically-linked* /bin/sh and /bin/sleep, plus their
# shared-library closure, into this fixture's sandbox runtime.
#
# Deliberately not the static busybox that examples/stage_runtimes.sh
# uses. This fixture exists to exercise Plane 2, and `LD_PRELOAD` only
# affects dynamically-linked executables - a static busybox builds fine
# and produces a trace with zero processes in it (tried first; it does).
#
# `sleep` is here for two reasons beyond running a command: `dash`
# leaves the shell through `_exit()`, which bypasses libc's exit path so
# the shim's destructor never fires, and a build made only of `sh -c`
# wrappers yields START lines with no END - no measurable sandbox
# interval, and nothing for `bga correlate` to match on. `sleep` exits
# normally, so it closes a record, and it makes the element's span
# longer than Plane 1's millisecond log resolution.
#
# Binaries are staged, never committed: they are host-specific, and this
# is the same rule examples/stage_runtimes.sh follows.
#
# Usage: stage_runtime.sh [DEST]   (DEST defaults to this fixture's own
# files/runtime; the acceptance test passes a throwaway copy.)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${1:-${HERE}/files/runtime}"

mkdir -p "${DEST}/bin"

stage() {  # stage <source binary> <name under bin/>
    local src="$1" name="$2"
    # `ldd` is the test rather than `file`: it is what the loader itself
    # would do, it is present wherever a toolchain is, and on a static
    # binary it says so and fails.
    if ! ldd "$src" >/dev/null 2>&1; then
        echo "stage_runtime.sh: $src is not dynamically linked - see this script's header" >&2
        exit 1
    fi
    cp "$src" "${DEST}/bin/${name}"
    # The closure, at the absolute paths the loader will look for it at
    # inside the sandbox.
    ldd "$src" | awk '{for (i = 1; i <= NF; i++) if ($i ~ /^\//) print $i}' | sort -u | while read -r lib; do
        mkdir -p "${DEST}$(dirname "$lib")"
        [ -e "${DEST}${lib}" ] || cp "$lib" "${DEST}${lib}"
    done
}

# `dash` for preference because it is the smallest real shell that is
# dynamically linked on a Debian-family host; any dynamically-linked
# shell does the job.
SH_SRC=""
for candidate in /bin/dash /bin/bash "$(command -v sh)"; do
    if [ -x "$candidate" ] && ldd "$candidate" >/dev/null 2>&1; then
        SH_SRC="$candidate"
        break
    fi
done
if [ -z "$SH_SRC" ]; then
    echo "stage_runtime.sh: found no dynamically-linked shell to stage" >&2
    exit 1
fi

stage "$SH_SRC" sh
stage "$(command -v sleep)" sleep
