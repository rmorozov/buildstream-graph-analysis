#!/bin/sh
# UX-848: generates this element's C sources *inside the sandbox*, at
# configure time - not committed, so the tree stays small (the task
# file's own decision). Emits $2 (default 64) arithmetic-heavy
# translation units under name $1, a header, a main() calling every one,
# and a plain hand-written Makefile - stage_cpp_toolchain.sh does not
# stage autoconf/automake/libtool, and this project's `kind: autotools`
# element only needs its already-safe MAKEFLAGS/V nocache declaration
# (autotools.yaml), not a real autoreconf.
#
# $1 must be a valid C identifier (used verbatim as a symbol/header-
# guard prefix, e.g. `mod_a` - not `mod-a`: `x-y_probe_00` parses as
# subtraction, confirmed via a real "implicit declaration" + "Error 1"
# build failure). No `tr`/`sed` staged to fix a bad one up at run time
# (stage_cpp_toolchain.sh's BINARIES list has neither) - the caller is
# responsible for passing one.
#
# POSIX sh only (dash on this host) - stage_cpp_toolchain.sh stages
# /usr/bin/sh but no python/awk/seq.
set -eu

NAME="$1"
COUNT="${2:-64}"
LINES="${3:-1800}"

i=0
while [ "$i" -lt "$COUNT" ]; do
  n=$(printf '%02d' "$i")
  {
    printf '#include "%s.h"\n' "$NAME"
    printf 'unsigned int %s_probe_%s(unsigned int x) {\n' "$NAME" "$n"
    j=0
    while [ "$j" -lt "$LINES" ]; do
      printf '  x = x * 1664525u + 1013904223u + %su + %su;\n' "$i" "$j"
      j=$((j + 1))
    done
    printf '  return x;\n}\n'
  } > "unit_${n}.c"
  i=$((i + 1))
done

{
  printf '#ifndef %s_H\n#define %s_H\n' "$NAME" "$NAME"
  i=0
  while [ "$i" -lt "$COUNT" ]; do
    n=$(printf '%02d' "$i")
    printf 'unsigned int %s_probe_%s(unsigned int x);\n' "$NAME" "$n"
    i=$((i + 1))
  done
  printf '#endif\n'
} > "${NAME}.h"

{
  printf '#include <stdio.h>\n#include "%s.h"\n\n' "$NAME"
  printf 'int main(void) {\n  unsigned int acc = 0;\n'
  i=0
  while [ "$i" -lt "$COUNT" ]; do
    n=$(printf '%02d' "$i")
    printf '  acc += %s_probe_%s(acc + %su);\n' "$NAME" "$n" "$i"
    i=$((i + 1))
  done
  printf '  printf("%%u\\n", acc);\n  return 0;\n}\n'
} > main.c

{
  printf 'NAME := %s\n' "$NAME"
  printf 'CFLAGS ?= -O1\n'
  printf 'OBJS := $(patsubst %%.c,%%.o,$(wildcard *.c))\n\n'
  printf 'all: $(NAME)\n\n'
  printf '$(NAME): $(OBJS)\n\t$(CC) -o $@ $(OBJS)\n\n'
  printf '%%.o: %%.c\n\t$(CC) $(CFLAGS) -c -o $@ $<\n\n'
  # `mkdir`/`cp` are not staged (stage_cpp_toolchain.sh's BINARIES list
  # has neither) - `cmake -E`'s self-contained make_directory/copy
  # subcommands are, via toolchain.bst, same reasoning as cmake's own
  # `--target install` (cmake.yaml) never shelling out to either.
  printf 'install:\n\tcmake -E make_directory "$(DESTDIR)/usr/bin"\n\tcmake -E copy "$(NAME)" "$(DESTDIR)/usr/bin/$(NAME)"\n\n'
  printf 'clean:\n\trm -f $(OBJS) $(NAME)\n'
} > Makefile
