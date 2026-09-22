#!/usr/bin/env bash
# Populates examples/05-cmake-cpp-toolchain/files/toolchain/ with a real,
# working GCC + CMake + GNU Make toolchain, staged from this *host's* own
# installed packages (Ubuntu) rather than a container/Alpine pull - no
# docker/debootstrap/network image pull needed, and this host already has
# real gcc/g++/cmake/make/binutils installed (confirmed: this is how
# examples/05's own real C/C++ builds actually compile). BuildStream's
# sandbox binds in nothing from the host except staged dependencies (same
# reasoning as stage_runtimes.sh's busybox staging, scaled up to a full
# toolchain) - so every binary, shared library, gcc-internal helper
# (cc1/cc1plus/collect2), and header search path gcc/cmake hardcode has to
# be present in the sandbox at the exact same absolute path it has on the
# host (gcc's internal search paths are compiled in, not relocatable), so
# this stages a full mini sysroot preserving absolute paths.
#
# See examples/README.md's own `05-cmake-cpp-toolchain` section for how
# to use the result (an earlier revision of this header pointed at a
# `docs/backlog/scenarios/UX-08-...md` and a per-example README.md, neither of
# which was ever written - UX-08 was never filed, see
# docs/backlog/scenarios/README.md).
#
# examples/06-macro-micro-optimization needs the same sysroot in two
# more places (its own files/toolchain and its optimized/ variant's), so
# this script stages once and hardlink-clones into each of them - real
# copies as far as BuildStream is concerned, ~0 extra disk.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HERE/05-cmake-cpp-toolchain/files/toolchain"
rm -rf "$DEST"
mkdir -p "$DEST"

# Real binaries this project's cmake/make elements invoke directly, plus
# the gcc-internal helpers gcc itself execs (cc1/cc1plus/collect2 - found
# via `gcc -print-prog-name=...`, not on $PATH).
#
# UX-914: two axes, declared separately rather than one list, because
# they are blocked on different questions. The RUNTIME decides what a
# recipe's own shell and `make` do - it is where `style_for_make_version`
# reads (UX-874) and where the one pin below lives. The TOOLCHAIN decides
# what the compiled program is; replacing it with a relocatable cross
# toolchain is UX-925, and this split is what lets that happen without
# touching the runtime. tools/sysroot_manifest.py declares which package
# each name comes from and at what version, and verifies it below.
# UX-915: `make` is in neither array - it is pinned, not taken from this
# host.
RUNTIME_BINARIES=(
  /usr/bin/env /usr/bin/sh /usr/bin/uname /usr/bin/sort /usr/bin/cat
)
TOOLCHAIN_BINARIES=(
  /usr/bin/gcc /usr/bin/g++ /usr/bin/cc /usr/bin/c++
  /usr/bin/cmake /usr/bin/ld /usr/bin/ld.bfd
  /usr/bin/as /usr/bin/ar /usr/bin/ranlib /usr/bin/nm /usr/bin/strip
  $(gcc -print-prog-name=cc1) $(gcc -print-prog-name=cc1plus)
  $(gcc -print-prog-name=collect2)
)
BINARIES=( "${RUNTIME_BINARIES[@]}" "${TOOLCHAIN_BINARIES[@]}" )

copy_file_only() {
  local src="$1"
  [ -e "$src" ] || return 0
  local dest="$DEST$src"
  mkdir -p "$(dirname "$dest")"
  cp -a --parents -- "$src" "$DEST" 2>/dev/null || cp -a "$src" "$dest"
}

# Many paths here are symlinks - g++/gcc/cc/c++ through /etc/alternatives/*
# to a versioned real binary (e.g. g++-13), and *every* .so found via ldd
# is potentially a `libfoo.so -> libfoo.so.1 -> libfoo.so.1.2.3`-style
# versioned symlink chain, INCLUDING the dynamic linker itself
# (/lib64/ld-linux-x86-64.so.2 -> ../lib/x86_64-linux-gnu/ld-linux-x86-64.so.2
# on this host). Staging only the final resolved target - or only the
# first hop - leaves a dangling symlink in the sandbox: the kernel then
# reports a plain, misleading "No such file or directory" execve failure
# for the *referencing* binary, not an obviously-broken-symlink error
# (confirmed via real trial and error - this broke every single
# dynamically-linked binary in the sandbox, not just the one whose
# interpreter symlink was actually dangling). Walk and stage every hop, so
# every call site below uses this instead of copy_file_only directly.
copy_symlink_chain() {
  local path="$1"
  local seen=0
  while [ -L "$path" ] && [ "$seen" -lt 10 ]; do
    copy_file_only "$path"
    local target
    target="$(readlink -- "$path")"
    case "$target" in
      /*) path="$target" ;;
      # Lexical (`realpath -s`, no symlink resolution) join+normalize -
      # NOT `readlink -f`/`realpath` (symlink-resolving), which on this
      # usrmerged host (/lib64 -> usr/lib64, /lib -> usr/lib) jumps clean
      # past intermediate hops to a DIFFERENT real path than the one this
      # specific symlink's own text implies, leaving that intermediate
      # hop's own real location unstaged (confirmed via real trial and
      # error: every dynamically-linked binary failed to exec until this
      # was single-hop, lexical-only resolution).
      *) path="$(realpath -s -- "$(dirname "$path")/$target")" ;;
    esac
    seen=$((seen + 1))
  done
  copy_file_only "$path"
}

# Recursively resolve and stage every shared library a binary needs (ldd),
# plus the binary itself and the dynamic linker.
declare -A SEEN
stage_binary_closure() {
  local bin="$1"
  [ -e "$bin" ] || { echo "warning: missing $bin" >&2; return 0; }
  copy_symlink_chain "$bin"
  local real
  real="$(readlink -f -- "$bin")"
  while read -r lib; do
    [ -z "$lib" ] && continue
    [ -n "${SEEN[$lib]:-}" ] && continue
    SEEN[$lib]=1
    copy_symlink_chain "$lib"
  done < <(ldd "$real" 2>/dev/null | grep -oP '(?<==> )/\S+|^\s*/\S+' | sed 's/^\s*//')
}

for b in "${BINARIES[@]}"; do
  stage_binary_closure "$b"
done

# The dynamic linker itself (ldd doesn't list it for the "interpreter"
# line uniformly across all binaries, so stage it explicitly).
for interp in /lib64/ld-linux-x86-64.so.2 /lib/ld-linux.so.2; do
  [ -e "$interp" ] && copy_symlink_chain "$interp"
done

# gcc/g++'s own internal tree (crt*.o startup objects, libgcc.a,
# target-specific headers) - hardcoded search path, must exist verbatim.
# Staged wholesale (not just the specific binaries BINARIES cherry-picks)
# because collect2 (the real link driver, confirmed via `g++ -v`) also
# needs liblto_plugin.so from *both* /usr/lib/gcc/.../<ver>/ and
# /usr/libexec/gcc/.../<ver>/ - cherry-picking individual binaries missed
# it (confirmed via a real "liblto_plugin.so not found" link failure).
GCC_VER="$(gcc -dumpversion | cut -d. -f1)"
GCC_LIBDIR="/usr/lib/gcc/x86_64-linux-gnu/$GCC_VER"
GCC_LIBEXECDIR="/usr/libexec/gcc/x86_64-linux-gnu/$GCC_VER"
[ -d "$GCC_LIBDIR" ] && cp -a --parents "$GCC_LIBDIR" "$DEST"
[ -d "$GCC_LIBEXECDIR" ] && cp -a --parents "$GCC_LIBEXECDIR" "$DEST"
cp -a --parents /usr/lib/bfd-plugins "$DEST" 2>/dev/null || true

# Link-time-only files: crt*.o startup objects and the unversioned dev
# `.so`/.a symlinks/archives for libc/libm/libpthread/libdl/libgcc_s/
# libstdc++ - `ldd`'s runtime closure above only captures the *versioned*
# `.so.N` files an already-linked binary needs, never the unversioned dev
# symlinks or `.o`/`.a` files a *fresh link* needs (confirmed via a real
# "cannot find Scrt1.o"/"-lm: No such file" link failure - these are a
# genuinely separate dependency class from ldd's runtime closure).
MULTIARCH_LIBDIR="/usr/lib/x86_64-linux-gnu"
# Modern glibc's libc.so/libm.so "dev" files aren't symlinks or ELF at
# all - they're plain-text GNU ld linker scripts (`GROUP ( real.so.N
# AS_NEEDED ( other.so.N ) )`) that embed further absolute paths inline
# (confirmed via a real "cannot find libmvec.so.1" link failure - libm.so
# is textually `GROUP ( .../libm.so.6 AS_NEEDED ( .../libmvec.so.1 ) )`,
# and neither symlink-chain-walking nor ldd against an already-linked
# binary discovers a AS_NEEDED-only, link-time-only reference like this).
stage_maybe_linker_script() {
  local f="$1"
  copy_symlink_chain "$f"
  [ -e "$f" ] || return 0
  local real_f
  real_f="$(readlink -f -- "$f")"
  if file "$real_f" 2>/dev/null | grep -q "ASCII text"; then
    while read -r ref; do
      [ -z "$ref" ] && continue
      [ -n "${SEEN[$ref]:-}" ] && continue
      SEEN[$ref]=1
      stage_maybe_linker_script "$ref"
    done < <(grep -oP '/\S+\.(so|so\.\d+|a)\b' "$real_f" 2>/dev/null)
  else
    # A real ELF .so.N can still pull in further transitive runtime libs
    # ldd against the BINARIES list above never exercised (nothing in it
    # links this library directly).
    while read -r lib; do
      [ -z "$lib" ] && continue
      [ -n "${SEEN[$lib]:-}" ] && continue
      SEEN[$lib]=1
      copy_symlink_chain "$lib"
    done < <(ldd "$real_f" 2>/dev/null | grep -oP '(?<==> )/\S+|^\s*/\S+' | sed 's/^\s*//')
  fi
}

for f in "$MULTIARCH_LIBDIR"/crt1.o "$MULTIARCH_LIBDIR"/crti.o "$MULTIARCH_LIBDIR"/crtn.o \
         "$MULTIARCH_LIBDIR"/Scrt1.o "$MULTIARCH_LIBDIR"/gcrt1.o "$MULTIARCH_LIBDIR"/Mcrt1.o \
         "$MULTIARCH_LIBDIR"/libc.so "$MULTIARCH_LIBDIR"/libc_nonshared.a \
         "$MULTIARCH_LIBDIR"/libm.so "$MULTIARCH_LIBDIR"/libpthread.so \
         "$MULTIARCH_LIBDIR"/libdl.so "$MULTIARCH_LIBDIR"/libgcc_s.so \
         "$MULTIARCH_LIBDIR"/libstdc++.so "$MULTIARCH_LIBDIR"/libstdc++.so.6 \
         "$MULTIARCH_LIBDIR"/librt.so "$MULTIARCH_LIBDIR"/libutil.so; do
  stage_maybe_linker_script "$f"
done

# Standard C/C++ headers (multiarch bits-* headers included).
cp -a --parents /usr/include "$DEST"

# cmake's own data files (Modules/, Templates/) - located relative to the
# cmake binary's real install prefix, required at runtime.
#
# Two real, failed attempts before this one, both against `cmake
# --system-information`'s own reported CMAKE_ROOT (parsed via regex):
#   1. Plain `cp -a --parents "$CMAKE_ROOT"` - a real CI run on a
#      different host copied "successfully" (no error) but the Modules/
#      subtree was unusable at build time ("CMake Error: Could not find
#      CMAKE_ROOT !!! ... Modules directory not found").
#   2. `cp -aL` (dereference symlinks) instead, on the theory the tree
#      was nested behind a symlink `-a` preserved as a dangling shell -
#      identical failure on a re-run, so that theory was wrong.
# Root cause, from actually reading `dpkg -L cmake-data` on this host:
# cmake-data is a real, dpkg-authoritative package that owns this exact
# directory - using it directly sidesteps needing `--system-information`
# to work correctly (it launches cmake and does a real trial compile,
# more moving parts than a plain dpkg query) or its text output to be
# regex-parseable in the exact expected shape on every host.
CMAKE_VER_DIR=""
if command -v dpkg >/dev/null 2>&1 && dpkg -s cmake-data >/dev/null 2>&1; then
  # `pipefail` + `grep -m1` is a real footgun here: grep exiting after its
  # first match closes the pipe early, so `dpkg` gets SIGPIPE and exits
  # 141 - under `pipefail` that's the pipeline's reported status even
  # though grep itself succeeded, which `set -e` then treats as this
  # whole command failing (confirmed via a real silent-abort right after
  # this line). Disable pipefail for just this one command instead of
  # restructuring around `-m1`.
  set +o pipefail
  CMAKE_VER_DIR="$(dpkg -L cmake-data 2>/dev/null | grep -m1 -P '^/usr/share/cmake-[0-9][0-9.]*$' || true)"
  set -o pipefail
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    copy_file_only "$f"
  done < <(dpkg -L cmake-data 2>/dev/null | grep '^/usr/share/cmake-')
fi
# Fallback for non-dpkg hosts (or if the package query above found
# nothing) - the original detection approach, kept only as a last resort.
if [ -z "$CMAKE_VER_DIR" ]; then
  CMAKE_DATADIR="$(cmake --system-information 2>/dev/null | grep -oP '(?<=CMAKE_ROOT ")[^"]+' | head -1)"
  rm -rf "$HERE/__cmake_systeminformation"
  if [ -n "${CMAKE_DATADIR:-}" ] && [ -d "$CMAKE_DATADIR" ]; then
    cp -aL --parents "$CMAKE_DATADIR" "$DEST"
    CMAKE_VER_DIR="$CMAKE_DATADIR"
  fi
fi

# `make`'s own recipe shell is hardcoded to /bin/sh (confirmed via a real
# "make[1]: /bin/sh: No such file or directory" failure) - this host
# aliases /bin -> usr/bin (usrmerge) but BuildStream's sandbox only stages
# exactly what's in this tree, so the alias has to be real staged content,
# not something supplied by a bwrap flag at smoke-test time.
ln -sfn usr/bin "$DEST/bin"

# UX-915: the sandbox's `make` version decides every example's jobserver
# auth style (`style_for_make_version`, UX-874), so it is pinned here
# rather than copied from whatever the staging host installed. Ubuntu
# 24.04 ships 4.3, below UX-841's 4.4 cutoff, so the `fifo` branch had
# never run in this repository's own examples and each jobserver
# element carried a `public: bga: jobserver-auth: fd` override standing
# in for that host fact. tools/nix_store_fetch.py carries the pin, its
# checksum, and why a download beats a source build here.
# UX-916 stages a 4.2 beside it, at /usr/lib/bga-make/<series>/make,
# so an element can name a version series without naming a pin hash;
# /usr/bin/make - what every element resolves by default - is the 4.4.
PINNED_MAKE="$(cd "$HERE/.." && python3 -m tools.nix_store_fetch "$DEST")"
MAKE_STORE_PATH="$(printf '%s\n' "$PINNED_MAKE" | awk -F'\t' '$1 == "make-4.4" {print $2}')"
PINNED_MAKE_VERSION="$(printf '%s\n' "$PINNED_MAKE" | awk -F'\t' '$1 == "make-4.4" {print $3}')"
INTERPRETER_DIR="$(cd "$HERE/.." && python3 -m tools.nix_store_fetch --interpreter-dir "$DEST")"
# Relative, not absolute: an absolute /nix/store link dangles on the
# staging host, so the verification below - and `-e` in the MISSING
# check - could not follow it. Inside the sandbox both read the same.
rm -f "$DEST/usr/bin/make"
ln -s "../..$MAKE_STORE_PATH/bin/make" "$DEST/usr/bin/make"

# The pinned binary names an absolute Nix interpreter and RUNPATH, both
# answered by nix_store_fetch's one symlink into this sysroot's own
# glibc. Run it through exactly that path rather than trusting the
# symlink's shape: a staged make that cannot exec is the failure this
# whole script's loud-verification posture exists to catch early, and
# both pins stop at GLIBC_2.38 (`objdump -T`), which is what makes the
# host's own glibc a valid answer at all.
STAGED_MAKE_VERSION="$("$DEST$INTERPRETER_DIR/ld-linux-x86-64.so.2" \
  "$DEST/usr/bin/make" --version 2>&1 | head -1)"
if [ "$STAGED_MAKE_VERSION" != "$PINNED_MAKE_VERSION" ]; then
  echo "stage_cpp_toolchain.sh: the staged make reports" >&2
  echo "  $STAGED_MAKE_VERSION" >&2
  echo "but this repository pins $PINNED_MAKE_VERSION" >&2
  exit 1
fi
echo "Pinned $STAGED_MAKE_VERSION from $MAKE_STORE_PATH"
printf '%s\n' "$PINNED_MAKE" | awk -F'\t' '{print "  staged " $3 " as /usr/lib/bga-make/" substr($1, 6) "/make"}'

# Loud, early verification rather than a silent, "succeeded" staging step
# that turns out unusable three layers deep into a real build (exactly
# what happened above with cmake's Modules/ dir on a different host) -
# fail *here*, with a clear list of what's missing, not inside a cryptic
# cmake/gcc error during the real bst build this is staged for.
MISSING=()
for f in "$DEST/usr/bin/gcc" "$DEST/usr/bin/g++" "$DEST/usr/bin/cmake" "$DEST/usr/bin/make" \
         "$DEST/usr/bin/ld" "$DEST$CMAKE_VER_DIR/Modules/CMakeCXXInformation.cmake" \
         "$DEST$INTERPRETER_DIR/ld-linux-x86-64.so.2" \
         "$DEST/usr/include/c++"; do
  [ -e "$f" ] || MISSING+=("$f")
done
if [ "${#MISSING[@]}" -gt 0 ]; then
  echo "stage_cpp_toolchain.sh: staged toolchain is missing expected files:" >&2
  printf '  %s\n' "${MISSING[@]}" >&2
  exit 1
fi

# UX-914: what this sysroot actually is, per package and per axis, read
# off the staged copies rather than off this host. A *pinned* row that
# disagrees exits 1 (the pin did not take, same posture as the make check
# above); a *host* row that disagrees only warns, because a different
# working host is not a broken sysroot - it is a different program under
# measurement, and the guard is what reddens for that.
(cd "$HERE/.." && python3 -m tools.sysroot_manifest --check "$DEST")

# UX-930: the versions above say what the sysroot is; this says where
# its own driver actually reaches. Every one of gcc's path parameters
# falls back to a host absolute path when the parameterized location
# is empty, and none of them says so, so each file class is asked
# rather than assumed - the reading UX-925's -B/--sysroot route needs
# before it can move the driver out of this tree.
(cd "$HERE/.." && python3 -m tools.toolchain_params --check "$DEST")

echo "Staged toolchain to $DEST ($(du -sh "$DEST" | cut -f1))"

# Every other example project that needs the identical sysroot. Hardlink
# clones (`cp -al`), not copies: BuildStream stages them as ordinary
# files, and the content is byte-identical by construction, so paying for
# a second and third ~270MB of real disk buys nothing.
for clone in \
    "$HERE/06-macro-micro-optimization/files/toolchain" \
    "$HERE/06-macro-micro-optimization/optimized/files/toolchain" \
    "$HERE/07-declared-vs-used-dependencies/files/toolchain" \
    "$HERE/08-process-storm/files/toolchain" \
    "$HERE/09-fine-grained-siblings/files/toolchain" \
    "$HERE/09-fine-grained-siblings/merged/files/toolchain" \
    "$HERE/10-jobserver/files/toolchain" \
    "$HERE/11-serial-giant/files/toolchain" \
    "$HERE/12-junctioned/sub/files/toolchain"; do
  rm -rf "$clone"
  mkdir -p "$(dirname "$clone")"
  cp -al "$DEST" "$clone"
  echo "Cloned toolchain to $clone"
done

# UX-857: examples/11-serial-giant's cmake elements reuse 10-jobserver's
# own files/gen/cmake/generate.sh (a real, committed script - not a
# generated sysroot) rather than a second copy someone has to keep in
# sync - hardlink-cloned the same way the toolchain above is, so it is
# still a real file in 11's own project directory (BuildStream's local
# source refuses a path outside it) at ~0 extra disk.
GEN_SRC="$HERE/10-jobserver/files/gen/cmake"
GEN_DEST="$HERE/11-serial-giant/files/gen/cmake"
rm -rf "$GEN_DEST"
mkdir -p "$(dirname "$GEN_DEST")"
cp -al "$GEN_SRC" "$GEN_DEST"
echo "Cloned generator to $GEN_DEST"
