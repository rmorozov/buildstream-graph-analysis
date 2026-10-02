#!/usr/bin/env bash
# bga pilot kit (UX-1288): run bga in a team's CI, report-only, from one script.
#
#   bga-pilot.sh setup                 pinned install by commit, then `bga doctor`
#   bga-pilot.sh capture [-- CMD ...]  the build under `bga capture run`, bundle kept
#   bga-pilot.sh report                `bga compare` against the kept band, as a CI comment
#
# CI-agnostic: every switch is an environment variable with its default
# below, and docs/guides/pilot.md carries the one table of them. Report-only
# unless PILOT_ENFORCE=on: `report` exits 0 whatever the verdict.
set -uo pipefail

# --- switches: docs/guides/pilot.md "Every switch", one row each ---
: "${PILOT_BGA_COMMIT:=}"
: "${PILOT_BGA_REPO:=https://github.com/rmorozov/buildstream-graph-analysis}"
: "${PILOT_PROJECT:=.}"
: "${PILOT_TARGET:=}"
: "${PILOT_BUILD_TYPE:=review}"
: "${PILOT_BUILD_VARIANT:=}"
: "${PILOT_REVIEW_SAMPLE:=25}"
: "${PILOT_JOBSERVER:=off}"
: "${PILOT_ADMISSION:=off}"
: "${PILOT_TRACE_OPENS:=off}"
: "${PILOT_TRACE_SPINE:=off}"
: "${PILOT_BAND_WINDOW:=10}"
: "${PILOT_CROSS_HOST:=off}"
: "${PILOT_KEEP_DIR:=bga-pilot-kept}"
: "${PILOT_KEEP_LAST:=30}"
: "${PILOT_ENFORCE:=off}"
# --- end switches ---
WORK_DIR="${TMPDIR:-/tmp}/bga-pilot"

say() { printf 'bga-pilot: %s\n' "$*" >&2; }

on_off() {
    case "$2" in
        on | off) ;;
        *) say "$1=$2: expected on or off"; exit 2 ;;
    esac
}

check_switches() {
    on_off PILOT_ADMISSION "$PILOT_ADMISSION"
    on_off PILOT_TRACE_OPENS "$PILOT_TRACE_OPENS"
    on_off PILOT_CROSS_HOST "$PILOT_CROSS_HOST"
    on_off PILOT_ENFORCE "$PILOT_ENFORCE"
    case "$PILOT_TRACE_SPINE" in off | on | auto) ;; *) say "PILOT_TRACE_SPINE=$PILOT_TRACE_SPINE: expected off, on or auto"; exit 2 ;; esac
    case "$PILOT_JOBSERVER" in off | auto | [1-9] | [1-9][0-9] | [1-9][0-9][0-9]) ;; *) say "PILOT_JOBSERVER=$PILOT_JOBSERVER: expected off, auto or a token count"; exit 2 ;; esac
    case "$PILOT_REVIEW_SAMPLE" in [0-9] | [1-9][0-9] | 100) ;; *) say "PILOT_REVIEW_SAMPLE=$PILOT_REVIEW_SAMPLE: expected a percentage, 0-100"; exit 2 ;; esac
    case "$PILOT_BAND_WINDOW" in [3-9] | [1-9][0-9]) ;; *) say "PILOT_BAND_WINDOW=$PILOT_BAND_WINDOW: expected 3-99 runs"; exit 2 ;; esac
    case "$PILOT_KEEP_LAST" in [1-9] | [1-9][0-9] | [1-9][0-9][0-9]) ;; *) say "PILOT_KEEP_LAST=$PILOT_KEEP_LAST: expected a count of bundles"; exit 2 ;; esac
    if [ -z "$PILOT_BUILD_TYPE" ]; then say "PILOT_BUILD_TYPE is empty: name the build (night, review, ...)"; exit 2; fi
}

# One kept directory per comparison class, so a band never reads another class's bundles.
class_dir() {
    local variant="${PILOT_BUILD_VARIANT:-default}"
    printf '%s/%s/%s' "$PILOT_KEEP_DIR" "$PILOT_BUILD_TYPE" "$(printf '%s' "$variant" | tr ',=/ ' '_-__')"
}

cmd_setup() {
    case "$PILOT_BGA_COMMIT" in
        *[!0-9a-f]* | "") say "PILOT_BGA_COMMIT must be a full 40-character commit sha, got '$PILOT_BGA_COMMIT'"; exit 2 ;;
    esac
    if [ "${#PILOT_BGA_COMMIT}" -ne 40 ]; then
        say "PILOT_BGA_COMMIT must be a full 40-character commit sha, got ${#PILOT_BGA_COMMIT} characters"
        exit 2
    fi
    mkdir -p "$WORK_DIR"
    rm -f "$WORK_DIR/ready"
    python3 -m pip install --quiet "bga @ git+$PILOT_BGA_REPO@$PILOT_BGA_COMMIT" || { say "install failed"; exit 1; }
    # A failed doctor fails this step and leaves no `ready`: `capture` then runs the plain build.
    bga doctor "$PILOT_PROJECT" || { say "bga doctor failed: the build will run without bga"; exit 1; }
    touch "$WORK_DIR/ready"
}

cmd_capture() {
    local -a build
    if [ "$#" -gt 0 ]; then
        build=("$@")
    elif [ -n "$PILOT_TARGET" ]; then
        build=(bst build "$PILOT_TARGET")
    else
        say "nothing to build: set PILOT_TARGET or pass the command after --"
        exit 2
    fi
    mkdir -p "$WORK_DIR"
    rm -f "$WORK_DIR/candidate"

    local why=""
    if [ ! -e "$WORK_DIR/ready" ]; then
        why="setup did not pass"
    elif [ "$PILOT_BUILD_TYPE" = review ] && [ $((RANDOM % 100)) -ge "$PILOT_REVIEW_SAMPLE" ]; then
        why="not in the ${PILOT_REVIEW_SAMPLE}% review sample"
    fi
    if [ -n "$why" ]; then
        say "building without bga: $why"
        (cd "$PILOT_PROJECT" && "${build[@]}")
        return
    fi

    local stamp snapshot
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    snapshot="$WORK_DIR/$stamp"
    mkdir -p "$snapshot"
    export BGA_BUILD_TYPE="$PILOT_BUILD_TYPE"
    export BGA_BUILD_VARIANT="$PILOT_BUILD_VARIANT"
    if [ "$PILOT_ADMISSION" = on ]; then export BGA_ADMISSION=1; else unset BGA_ADMISSION; fi

    local -a capture=(--run-dir "$snapshot/run" --host-samples "$snapshot/host-samples.jsonl"
        --jobserver "$PILOT_JOBSERVER" --trace-spine "$PILOT_TRACE_SPINE")
    if [ "$PILOT_TRACE_OPENS" = on ]; then capture+=(--trace-opens); fi

    local rc=0
    bga capture run "${capture[@]}" "$PILOT_PROJECT" "$snapshot/plane2.json" -- "${build[@]}" || rc=$?

    # Keeping the bundle never fails the job; the build's own exit code does.
    if [ -d "$snapshot/run" ]; then
        local kept
        kept="$(class_dir)"
        mkdir -p "$kept"
        if bga bundle --export "$snapshot" -o "$kept/$stamp.bga-bundle.tar.gz" >&2; then
            printf '%s\n' "$snapshot" >"$WORK_DIR/candidate"
            local -a all=()
            mapfile -t all < <(find "$kept" -maxdepth 1 -name '*.bga-bundle.tar.gz' | sort)
            local drop=$((${#all[@]} - PILOT_KEEP_LAST)) i
            for ((i = 0; i < drop; i++)); do rm -f "${all[$i]}"; done
        else
            say "bundle export failed; this build is not kept"
        fi
    else
        say "the capture wrote no run directory; nothing to keep"
    fi
    return "$rc"
}

cmd_report() {
    local candidate kept
    if [ ! -s "$WORK_DIR/candidate" ]; then
        say "no capture this build; no comment"
        return 0
    fi
    candidate="$(cat "$WORK_DIR/candidate")"
    kept="$(class_dir)"
    local stamp baseline_bundle=""
    stamp="$(basename "$candidate")"
    local -a all=()
    mapfile -t all < <(find "$kept" -maxdepth 1 -name '*.bga-bundle.tar.gz' ! -name "$stamp.bga-bundle.tar.gz" | sort)
    if [ "${#all[@]}" -eq 0 ]; then
        say "first kept build of class $PILOT_BUILD_TYPE/${PILOT_BUILD_VARIANT:-default}; no baseline yet, no comment"
        return 0
    fi
    baseline_bundle="${all[${#all[@]} - 1]}"
    # Unpacked under its own stamp, so the band excludes it as it excludes the candidate.
    local baseline
    baseline="$WORK_DIR/baseline/$(basename "$baseline_bundle" .bga-bundle.tar.gz)"
    rm -rf "$WORK_DIR/baseline"
    mkdir -p "$baseline"
    tar -xzf "$baseline_bundle" -C "$baseline" --strip-components=1 capture/ \
        || { say "cannot unpack $baseline_bundle; no comment"; return 0; }

    local comment="$WORK_DIR/comment.md"
    local -a compare=("$baseline/run" "$candidate/run" --format ci-comment -o "$comment"
        --fail-on-regression --fail-on-efficiency-regression)
    if [ "$PILOT_CROSS_HOST" = on ]; then compare+=(--allow-cross-host); fi
    if [ "$PILOT_TRACE_OPENS" = on ] && [ -s "$candidate/plane2.json" ]; then
        compare+=(--native-report "$candidate/plane2.json")
    fi

    local rc=0 judged=band
    rm -f "$comment"
    bga compare "${compare[@]}" --band-from-class "$PILOT_BAND_WINDOW" --bundles "$kept" || rc=$?
    if [ "$rc" -eq 8 ]; then
        # Exit 8: under three kept runs of this class. The comment says it is the fixed 1% rule.
        say "band refused (exit 8): too few kept runs of this class yet; commenting against the fixed 1% rule"
        judged=rule
        rc=0
        bga compare "${compare[@]}" || rc=$?
    fi
    printf '%s\t%s\t%s\t%s\t%s\n' "$stamp" "$PILOT_BUILD_TYPE" "${PILOT_BUILD_VARIANT:-default}" "$judged" "$rc" \
        >>"$PILOT_KEEP_DIR/verdicts.tsv"
    if [ -s "$comment" ]; then
        cat "$comment"
    else
        say "bga compare exited $rc and wrote no comment"
    fi
    say "verdict exit $rc (judged against the $judged); report-only: PILOT_ENFORCE=$PILOT_ENFORCE"
    if [ "$PILOT_ENFORCE" = on ] && { [ "$rc" -eq 4 ] || [ "$rc" -eq 5 ]; }; then
        return "$rc"
    fi
    return 0
}

main() {
    local sub="${1:-}"
    [ "$#" -gt 0 ] && shift
    check_switches
    case "$sub" in
        setup) cmd_setup ;;
        capture)
            [ "${1:-}" = "--" ] && shift
            cmd_capture "$@"
            ;;
        report) cmd_report ;;
        *)
            say "usage: bga-pilot.sh setup | capture [-- CMD ...] | report"
            exit 2
            ;;
    esac
}

main "$@"
