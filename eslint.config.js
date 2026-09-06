"use strict";
// UX-699: no `npm install` lands in the tree (UX-397); plugins resolve
// as siblings of npx's own installed `eslint`, not of this file.
const { createRequire } = require("node:module");
const req = createRequire(process.argv[1]);
const importPlugin = req("eslint-plugin-import");
const globals = req("globals");

module.exports = [
  {
    files: ["bga/viewer/**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: globals.browser,
    },
    plugins: { import: importPlugin },
    rules: {
      eqeqeq: "error",
      "no-undef": "error",
      // `.eslintrc.json` is not this config; `no-unused-modules`'s own
      // legacy file lookup needs one to find `ignorePatterns` (import-js/eslint-plugin-import#3079).
      "import/no-unused-modules": ["error", { unusedExports: true }],
    },
  },
];
