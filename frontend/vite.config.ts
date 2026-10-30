import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const proxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8000';
  const host = env.VITE_HOST || 'localhost';

  return {
    plugins: [react()],
    server: {
      port: 5173,
      host,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    optimizeDeps: {
      include: ['pdfjs-dist'],
    },
  };
});
