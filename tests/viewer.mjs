// UX-337: the viewer's exports in one namespace, for tests that want a
// symbol rather than a module.
//
// Before the split, `app.js` held the formatters, the schema-hint
// readers and the whole table machinery, and `views.js` held every
// section including the element object and the decision panel - so a
// test that wanted `buildTable`, `quantity` or `renderCulprits`
// imported one of those two, and dozens did. The split moved them into
// `format.js`, `structured.js`, `element.js` and `decision.js` without
// changing a line of what they do. Re-pointing every snippet by hand
// would make a pure move read as a rewrite in the diff, and would do
// so again the next time a function changes module.
//
// What those tests mean is "the viewer", not "app.js". This file says
// that once, in the order the export inlines them. `bga/viewer/` itself
// must not re-export - `_module_order` walks `import` lines and cannot
// see the form, so a re-exported module is never inlined and its
// symbols are called and never declared (`UX-199`) - which is asserted
// in `test_the_viewer_splits_along_its_seams.py`. Nothing inlines this
// file: it exists only for Node under the DOM shim, and the same guard
// asserts it names every module the export knows about.
//
// No two of these modules export the same name; if two ever did,
// `export *` would drop the name silently, so the guard checks that
// too.
export * from "../bga/viewer/primitives.js";
export * from "../bga/viewer/format.js";
export * from "../bga/viewer/controls.js";
export * from "../bga/viewer/drawings.js";
export * from "../bga/viewer/shapes.js";
export * from "../bga/viewer/tablefocus.js";
export * from "../bga/viewer/tables.js";
export * from "../bga/viewer/views.js";
export * from "../bga/viewer/structured.js";
export * from "../bga/viewer/perfetto.js";
export * from "../bga/viewer/element.js";
export * from "../bga/viewer/decision.js";
export * from "../bga/viewer/chapters.js";
export * from "../bga/viewer/nav.js";
export * from "../bga/viewer/rawjson.js";
export * from "../bga/viewer/focus.js";
export * from "../bga/viewer/viewstate.js";
export * from "../bga/viewer/questions.js";
export * from "../bga/viewer/trace_context.js";
export * from "../bga/viewer/app.js";
