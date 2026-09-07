"use strict";
// UX-699: no `npm install` lands in the tree (UX-397); `globals`
// resolves as a sibling of npx's own installed `eslint`, not of this
// file.
const { createRequire } = require("node:module");
const req = createRequire(process.argv[1]);
const globals = req("globals");

module.exports = [
  {
    files: ["bga/viewer/**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: globals.browser,
    },
    rules: {
      eqeqeq: "error",
      "no-undef": "error",
    },
  },
];
