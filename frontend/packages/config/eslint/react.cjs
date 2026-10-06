/**
 * React / hooks 附加规则。业务代码统一 `extends: ['@xian/config/eslint/react']`。
 */
module.exports = {
  extends: ['./base.cjs'],
  plugins: ['react-hooks', 'react-refresh'],
  settings: { react: { version: '19' } },
  rules: {
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
    'react-refresh/only-export-components': ['warn', { allowConstantExport: true }]
  }
};