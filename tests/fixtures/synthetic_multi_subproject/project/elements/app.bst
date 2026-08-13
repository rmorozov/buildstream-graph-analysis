# Root C++ executable - links shared libraries pulled in from every
# subproject junction, including a diamond dependency on core-utils
# (reached both directly via liblog and transitively via libnet/libui).
kind: cmake
sources:
- kind: local
  path: files/app

depends:
- net-stack.bst:elements/libnet.bst
- ui-toolkit.bst:elements/libui.bst
- data-format.bst:elements/libxml.bst
- core-utils.bst:elements/liblog.bst
