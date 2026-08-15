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
# See docs/scenarios/UX-08-cmake-cpp-toolchain-example.md for the real
# trial-and-error this required and examples/05-cmake-cpp-toolchain/README.md
# for how to use the result.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HERE/05-cmake-cpp-toolchain/files/toolchain"
rm -rf "$DEST"
mkdir -p "$DEST"

# Real binaries this project's cmake/make elements invoke directly, plus
# the gcc-internal helpers gcc itself execs (cc1/cc1plus/collect2 - found
# via `gcc -print-prog-name=...`, not on $PATH).
BINARIES=(
  /usr/bin/gcc /usr/bin/g++ /usr/bin/cc /usr/bin/c++
  /usr/bin/cmake /usr/bin/make /usr/bin/ld /usr/bin/ld.bfd
  /usr/bin/as /usr/bin/ar /usr/bin/ranlib /usr/bin/nm /usr/bin/strip
  /usr/bin/env /usr/bin/sh /usr/bin/uname /usr/bin/sort /usr/bin/cat
  $(gcc -print-prog-name=cc1) $(gcc -print-prog-name=cc1plus)
  $(gcc -print-prog-name=collect2)
)

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
# cmake binary's real install prefix, required at runtime. `-L` (dereference
# symlinks) rather than plain `-a`: a real CI run on a different host found
# this directory copied "successfully" (no error) but with the Modules/
# subtree unusable ("CMake Error: Could not find CMAKE_ROOT !!! ... Modules
# directory not found") - that host's cmake package apparently has this
# tree nested behind a symlink `-a` preserves as a shell rather than
# following, unlike this dev host's own real, non-symlinked layout.
CMAKE_DATADIR="$(cmake --system-information 2>/dev/null | grep -oP '(?<=CMAKE_ROOT ")[^"]+' | head -1)"
rm -rf "$HERE/__cmake_systeminformation"
if [ -n "${CMAKE_DATADIR:-}" ] && [ -d "$CMAKE_DATADIR" ]; then
  cp -aL --parents "$CMAKE_DATADIR" "$DEST"
fi

# `make`'s own recipe shell is hardcoded to /bin/sh (confirmed via a real
# "make[1]: /bin/sh: No such file or directory" failure) - this host
# aliases /bin -> usr/bin (usrmerge) but BuildStream's sandbox only stages
# exactly what's in this tree, so the alias has to be real staged content,
# not something supplied by a bwrap flag at smoke-test time.
ln -sfn usr/bin "$DEST/bin"

# Loud, early verification rather than a silent, "succeeded" staging step
# that turns out unusable three layers deep into a real build (exactly
# what happened above with cmake's Modules/ dir on a different host) -
# fail *here*, with a clear list of what's missing, not inside a cryptic
# cmake/gcc error during the real bst build this is staged for.
MISSING=()
for f in "$DEST/usr/bin/gcc" "$DEST/usr/bin/g++" "$DEST/usr/bin/cmake" "$DEST/usr/bin/make" \
         "$DEST/usr/bin/ld" "$DEST$CMAKE_DATADIR/Modules/CMakeCXXInformation.cmake" \
         "$DEST/usr/include/c++"; do
  [ -e "$f" ] || MISSING+=("$f")
done
if [ "${#MISSING[@]}" -gt 0 ]; then
  echo "stage_cpp_toolchain.sh: staged toolchain is missing expected files:" >&2
  printf '  %s\n' "${MISSING[@]}" >&2
  exit 1
fi

echo "Staged toolchain to $DEST ($(du -sh "$DEST" | cut -f1))"
