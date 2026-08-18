# Step 1 of an unnecessarily-split two-step "prepare" prelude (see
# base-generate.bst) - a real, common anti-pattern: two config/generate
# steps that could just as well be one, each adding real serial time to
# the critical path before core.bst can even start. The optimized/
# variant merges both into a single, shorter step. See
# docs/guides/optimization-walkthrough.md.
kind: manual
depends:
- filename: runtime.bst
  type: build
config:
  install-commands:
  - "sleep 1"
