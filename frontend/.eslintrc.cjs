module.exports = {
  root: true,

  env: {
    browser: true,
    es2021: true,
    node: true,
  },

  parser: "@typescript-eslint/parser",

  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    ecmaFeatures: {
      jsx: true,
    },
  },

  plugins: [
    "@typescript-eslint",
    "react-hooks",
    "react-refresh",
  ],

  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
  ],

  rules: {
    // Allow existing TypeScript code to use `any`.
    "@typescript-eslint/no-explicit-any": "off",

    // Don't fail CI over unused variables.
    "@typescript-eslint/no-unused-vars": "off",

    // TypeScript handles undefined-name checking.
    "no-undef": "off",

    // React Hooks checks.
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "off",

    // React Fast Refresh checks.
    "react-refresh/only-export-components": "off",
  },

  ignorePatterns: [
    "node_modules/",
    "dist/",
    "*.d.ts",
    "vite.config.ts",
    "vite.config.js",
  ],
};