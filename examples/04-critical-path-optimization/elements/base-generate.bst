# Step 2 of the unnecessarily-split prelude - depends on base-config.bst
# purely for sequencing (no real data dependency between them). See
# docs/guides/optimization-walkthrough.md.
kind: manual
depends:
- filename: base-config.bst
  type: build
- filename: runtime.bst
  type: build
config:
  install-commands:
  - "sleep 1"
