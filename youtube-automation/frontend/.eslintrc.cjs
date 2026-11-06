module.exports = {
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  parser: require.resolve('vue-eslint-parser'),
  parserOptions: {
    parser: require.resolve('@typescript-eslint/parser'),
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  extends: ['eslint:recommended', 'plugin:vue/vue3-recommended'],
  rules: {
    'vue/multi-word-component-names': 'off',
    'vue/no-v-html': 'error',
    'vue/html-closing-bracket-newline': 'off',
    'vue/html-self-closing': 'off',
    'vue/max-attributes-per-line': 'off',
    'vue/singleline-html-element-content-newline': 'off',
  },
}
