import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Relative base + hash routing: the build works on any GitHub Pages path.
export default defineConfig({
  base: './',
  plugins: [react()],
});
