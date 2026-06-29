/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/api/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Use function syntax for more control over chunk splitting
        manualChunks(id: string) {
          // Vendor chunk for MUI and Emotion (includes React dependencies)
          if (id.includes('node_modules') &&
              (id.includes('@mui') || id.includes('@emotion'))) {
            return 'vendor-mui';
          }

          // Vendor chunk for Recharts
          if (id.includes('node_modules/recharts')) {
            return 'vendor-recharts';
          }

          // Vendor chunk for D3 modules (used by react-d3-tree)
          if (id.includes('node_modules/react-d3-tree') ||
              id.includes('node_modules/d3-')) {
            return 'vendor-d3';
          }
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    css: true,
  },
});
