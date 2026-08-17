# The TRUE NEGATIVE case: declares base.bst and genuinely consumes it.
# `files/user/user.cpp` does `#include <base.hpp>`, which resolves to
# base.bst's staged /usr/include/base.hpp - so a real traced build opens
# exactly one of base.bst's five staged files, and UX-46 must NOT report
# this edge as unused.
kind: cmake
depends:
- filename: base.bst
  type: build
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/user
variables:
  generator: Unix Makefiles
