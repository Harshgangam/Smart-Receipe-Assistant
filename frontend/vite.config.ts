/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err, _req, res) => {
            if ((err as any).code === 'ECONNREFUSED') {
              if (res && 'writeHead' in res && !(res as any).headersSent) {
                (res as any).writeHead(503, { 'Content-Type': 'application/json' });
                (res as any).end(JSON.stringify({ error: 'Backend initializing, please wait...' }));
              }
              return;
            }
            console.error('Vite Proxy Error:', err);
          });
        },
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', (err, _req, res) => {
            if ((err as any).code === 'ECONNREFUSED') {
              if (res && 'writeHead' in res && !(res as any).headersSent) {
                (res as any).writeHead(503, { 'Content-Type': 'application/json' });
                (res as any).end(JSON.stringify({ status: 'initializing' }));
              }
              return;
            }
            console.error('Vite Proxy Error:', err);
          });
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true,
      },
    },
  },
});
