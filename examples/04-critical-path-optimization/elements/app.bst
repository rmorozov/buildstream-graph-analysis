# Final real build step - needs all four libraries.
kind: manual
depends:
- filename: lib-a.bst
  type: build
- filename: lib-b.bst
  type: build
- filename: lib-c.bst
  type: build
- filename: lib-d.bst
  type: build
- filename: runtime.bst
  type: build
config:
  install-commands:
  - "sleep 1"
