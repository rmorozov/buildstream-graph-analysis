#!/bin/sh
# UX-848: same generation as ../autotools/generate.sh (see its header) -
# $1 must be a valid C identifier (e.g. `mod_c`, not `mod-c`) - emitting
# a CMakeLists.txt instead of a Makefile. This pair's `kind: cmake`
# elements build with cmake's own already-safe JOBS nocache declaration
# (cmake.yaml) rather than MAKEFLAGS.
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
  printf 'cmake_minimum_required(VERSION 3.10)\n'
  printf 'project(%s C)\n' "$NAME"
  printf 'file(GLOB SOURCES "*.c")\n'
  printf 'add_executable(%s ${SOURCES})\n' "$NAME"
  printf 'install(TARGETS %s RUNTIME DESTINATION bin)\n' "$NAME"
} > CMakeLists.txt
