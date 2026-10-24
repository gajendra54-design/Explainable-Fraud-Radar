import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins: [react()], build: { rollupOptions: { output: { manualChunks: { charts: ["recharts"], vendor: ["react", "react-dom", "@tanstack/react-query"] } } } }, server: { host: '127.0.0.1', port: 5177, strictPort: true, proxy: { '/api': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8017' } } });
