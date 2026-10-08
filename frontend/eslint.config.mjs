import reactHooks from "eslint-plugin-react-hooks";
import parser from "@typescript-eslint/parser";

/**
 * 前端 lint 配置（flat config）。
 *
 * 只开「正确性」规则，不施加代码风格约束：
 * - rules-of-hooks：提前 return 之后再调 hook 会让 React 抛
 *   "Rendered fewer hooks than expected" 直接整页白屏，而 typecheck 与单测都抓不到，
 *   这条规则是唯一的静态防线。
 * - exhaustive-deps：依赖漏写导致闭包读到陈旧值。
 */
export default [
  { ignores: ["**/dist/**", "**/build/**", "**/coverage/**", "**/storybook-static/**"] },
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: {
      parser,
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } }
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn"
    }
  }
];
