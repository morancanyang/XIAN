import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [react()],
  /* 相对基路径：Capacitor / APK 中页面由本地 WebView 加载，绝对路径 /assets 无法解析 */
  base: './',
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@xian/ui': fileURLToPath(new URL('../../packages/ui/src', import.meta.url)),
      '@xian/types': fileURLToPath(new URL('../../packages/types/src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: process.env.VITE_API_PROXY ?? 'http://127.0.0.1:8000', changeOrigin: true },
      '/ws': { target: process.env.VITE_API_PROXY ?? 'http://127.0.0.1:8000', ws: true }
    }
  },
  build: {
    target: 'es2022',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          charts: ['echarts'],
          flow: ['@xyflow/react']
        }
      }
    }
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.{ts,tsx}']
  }
});