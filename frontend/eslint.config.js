import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import i18next from 'eslint-plugin-i18next';

export default tseslint.config(
  {
    ignores: [
      'dist/',
      'node_modules/',
      'playwright.config.*',
      'vite.config.js',
      'public/sw.js',
      'scripts/',
      'android/',
      'ios/',
      '**/assets/public/**',
      'ios/App/App/public/',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
      'jsx-a11y': jsxA11y,
      i18next,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      '@typescript-eslint/no-unused-vars': 'off',
      'i18next/no-literal-string': ['warn', {
        mode: 'jsx-text-only',
        'jsx-attributes': { include: ['alt', 'aria-label', 'placeholder', 'title'] },
      }],
    },
  },
  {
    files: ['tests/**'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
  {
    files: ['tests/**', 'scripts/**', 'src/locales/**', '**/__tests__/**'],
    rules: {
      'i18next/no-literal-string': 'off',
    },
  },
);
