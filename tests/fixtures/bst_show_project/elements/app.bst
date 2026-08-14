# Two build dependencies (tests %{build-deps}'s multi-item, embedded-
# newline format) plus one runtime-only dependency reached through a
# junction (tests dependency-type extraction and junction-qualified
# naming together).
kind: import
sources:
- kind: local
  path: files/app
depends:
- filename: base.bst
  type: build
- filename: base2.bst
  type: build
- filename: subproj-junction.bst:libfoo.bst
  type: runtime
