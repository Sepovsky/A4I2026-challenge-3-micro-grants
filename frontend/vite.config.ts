import { defineConfig } from 'vite';

// Serve the maintained console through the gateway during frontend development.
export default defineConfig({
  server: {
    port: 5173,
    host: '127.0.0.1',
    proxy: {
      '/console': { target: 'http://127.0.0.1:8080', rewrite: path => path.replace(/^\/console/, '') || '/' },
      '/api': 'http://127.0.0.1:8080',
      '/css': 'http://127.0.0.1:8080',
      '/js': 'http://127.0.0.1:8080',
    },
  },
});
