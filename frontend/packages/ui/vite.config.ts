import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';

/** @xian/ui 以源码形式被 workspace 消费，此配置仅用于独立构建与 Storybook 预览。 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@xian/ui': resolve(__dirname, 'src')
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      formats: ['es'],
      fileName: 'index'
    },
    rollupOptions: {
      external: ['react', 'react-dom', 'react/jsx-runtime', 'framer-motion', /^@radix-ui/]
    }
  }
});