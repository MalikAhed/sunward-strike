export default [{
  files: ['src/**/*.js'],
  languageOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    globals: Object.fromEntries(['window', 'location', 'document', 'console', 'performance', 'requestAnimationFrame', 'matchMedia', 'setTimeout', 'clearTimeout'].map(name => [name, 'readonly'])),
  },
  rules: { 'no-undef': 'error', 'no-unreachable': 'error', 'no-dupe-keys': 'error' },
}];
