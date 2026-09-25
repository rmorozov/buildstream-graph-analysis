#!/bin/sh
# UX-905 (`pairs`: off/auto) and UX-895 (`overhead`: none/capture/trace)
# on one quiet host: three interleaved repeats, cold caches every build,
# bst's own `max-jobs` default (min(cpus, 8)). One `::notice::` per arm
# at exit - GitHub keeps ten per step, a line per build would not fit.
set -eu
MODE=$1
PROJ=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-$PWD/arms}
mkdir -p "$OUT/xdg"
export XDG_CONFIG_HOME="$OUT/xdg"
printf 'cache:\n  quota: 20G\n  reserved-disk-space: 2G\n' > "$XDG_CONFIG_HOME/buildstream2.conf"
cd "$PROJ"

summary() {
    for arm in $(cut -d' ' -f1 "$OUT/builds.txt" 2>/dev/null | sort -u); do
        echo "::notice title=$MODE $arm::$(grep "^$arm " "$OUT/builds.txt" | cut -d' ' -f2- | paste -sd';' -)"
    done
}
trap summary EXIT

traced() {  # a capture whose hook never ran is not an arm (bwrap shim shadowed)
    python3 -c 'import json, sys; sys.exit(not json.load(open(sys.argv[1])).get("process_count"))' "$1"
}

peak() {
    python3 -c 'import json, sys
r = json.load(open(sys.argv[1]))
print(next((e.get("peak_work_concurrency") for e in r.get("per_element_parallelism") or []
            if e.get("element") == "giant.bst"), "?"))' "$1" 2>/dev/null || echo "?"
}

busy() {  # host-wide busy CPU seconds: the sandbox's work is not bst's rusage
    awk '/^cpu /{print ($2+$3+$4+$7+$8)/100}' /proc/stat
}

build() {  # build <arm> <repeat> <plane2 path or -> -- <command...>
    arm=$1 i=$2 plane2=$3; shift 4
    rm -rf ~/.cache/buildstream ~/.local/share/buildstream .bga
    b0=$(busy)
    /usr/bin/time -f '%e' -o "$OUT/time" "$@" > "$OUT/$arm-$i.log" 2>&1 \
        || { tail -40 "$OUT/$arm-$i.log"; exit 1; }
    b1=$(busy); read -r wall < "$OUT/time"
    [ "$plane2" = - ] || plane2=$(ls $plane2 2>/dev/null | tail -1)
    [ "$plane2" = - ] || traced "$plane2" || { echo "::error title=$arm::Plane 2 traced 0 processes"; exit 1; }
    p=$([ "$plane2" = - ] && echo - || peak "$plane2")
    cpu=$(python3 -c "print(f'{$b1 - $b0:.0f}')")
    echo "$arm wall ${wall}s cpu ${cpu}s giant-peak $p" | tee -a "$OUT/builds.txt"
}

for i in 1 2 3; do
    case $MODE in
    pairs)
        for m in off auto; do
            build "$m" "$i" "$OUT/$m-$i.json" -- bga capture run --run-dir "$OUT/run-$m-$i" \
                --jobserver "$m" . "$OUT/$m-$i.json" -- bst build all.bst
        done ;;
    overhead)
        build none "$i" - -- bst build all.bst
        build capture "$i" ".bga/runs/*/plane2.json" -- bga snapshot --no-trace-opens -- bst build all.bst
        build trace "$i" ".bga/runs/*/plane2.json" -- bga snapshot --trace-opens -- bst build all.bst ;;
    diag)  # one small auto capture, its report's shape printed whole
        build diag 1 "$OUT/diag.json" -- bga capture run --run-dir "$OUT/run-diag" --jobserver auto \
            . "$OUT/diag.json" -- bst --option giant_lines 1800 build all.bst
        tail -60 "$OUT/diag-1.log"
        python3 -c 'import json, sys
r = json.load(open(sys.argv[1]))
print("keys", sorted(r))
for k in ("per_element_parallelism", "jobserver_decisions", "jobserver_pool"):
    print(k, json.dumps(r.get(k))[:1500])' "$OUT/diag.json"
        find "$OUT/run-diag" -maxdepth 2 | head -40
        exit 0 ;;
    *) echo "usage: $0 pairs|overhead|diag" >&2; exit 2 ;;
    esac
done
