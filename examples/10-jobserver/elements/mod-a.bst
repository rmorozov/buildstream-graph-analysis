# One of two autotools elements (see mod-b.bst) - independent of every
# other mod-*.bst. `files/gen/autotools/generate.sh` (staged as this
# element's own source) writes 64 generated C files, a header, a main(),
# and a plain Makefile *inside the sandbox*, replacing the usual
# autogen+configure phase (stage_cpp_toolchain.sh stages no autoconf/
# automake/libtool - this element only needs `kind: autotools`'s own
# already-safe MAKEFLAGS/V nocache declaration, not a real autoreconf).
# `build-commands`/`install-commands` are left at the plugin's defaults,
# so `make`'s parallelism still comes from MAKEFLAGS (UX-848).
kind: autotools
depends:
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/gen/autotools
config:
  configure-commands:
  - sh generate.sh mod_a 64 1800
