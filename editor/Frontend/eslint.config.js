import js from '@eslint/js';
import pluginVue from 'eslint-plugin-vue';
import configPrettier from 'eslint-config-prettier';

export default [
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  configPrettier,
  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        requestAnimationFrame: 'readonly',
        cancelAnimationFrame: 'readonly',
        navigator: 'readonly',
        alert: 'readonly',
        URL: 'readonly',
        Blob: 'readonly',
        FileReader: 'readonly',
        atob: 'readonly',
        btoa: 'readonly',
        fetch: 'readonly',
        WebSocket: 'readonly',
        MutationObserver: 'readonly',
        ResizeObserver: 'readonly',
        process: 'readonly',
      },
    },
    rules: {
      // 该项目存在大量"暂未启用但保留以便恢复"的桥接函数与脚手架代码，
      // 整体关闭未使用变量告警；如需在新模块启用，可在该模块单独覆盖。
      'no-unused-vars': 'off',
      'vue/no-unused-vars': 'off',
      'vue/no-unused-components': 'off',
      'no-empty': ['warn', { allowEmptyCatch: true }],
      'no-console': 'off',
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'off',
      'vue/require-default-prop': 'off',
      'vue/attribute-hyphenation': 'off',
    },
  },
  {
    ignores: [
      'node_modules/**',
      'dist/**',
      'build/**',
      'src/blockly/configs/renderer.js',
    ],
  },
];
