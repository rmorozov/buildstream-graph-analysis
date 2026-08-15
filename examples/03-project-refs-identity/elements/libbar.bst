# The element whose source ref project.refs actually pins. No `ref:` key
# here deliberately - with ref-storage: project.refs, the resolved ref
# lives in project.refs, not in the element itself. `bst source track
# libbar.bst` (run by examples/stage_project3_remote.sh's caller, see
# examples/README.md) resolves the real commit SHA from the generated
# remote and writes it there.
kind: import
sources:
- kind: git
  url: "file://%{remote_path}"
  track: main
