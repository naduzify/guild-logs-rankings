import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Relative base + hash routing: the build works on any GitHub Pages path.
// One page per guild: / picks a guild, /fable/ is the Fable site, /nightshift/ is a placeholder.
export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        index: resolve(__dirname, 'index.html'),
        fable: resolve(__dirname, 'fable/index.html'),
        nightshift: resolve(__dirname, 'nightshift/index.html'),
      },
    },
  },
});
