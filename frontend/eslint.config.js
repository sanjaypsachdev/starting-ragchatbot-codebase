import js from "@eslint/js";

export default [
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2022,
      globals: {
        document: "readonly",
        window: "readonly",
        fetch: "readonly",
        console: "readonly",
        Date: "readonly",
        marked: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "warn",
      "no-console": "off",
    },
  },
];
