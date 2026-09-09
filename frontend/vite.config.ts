import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Прокси /api на backend нужен, чтобы на время разработки не настраивать CORS:
// браузер видит один источник http://localhost:5173.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    // Ant Design тяжёлый: разделяем бандлы, чтобы пересобирать их по отдельности
    // и не получать предупреждение о чанке больше 500 КБ.
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          antd: ['antd', '@ant-design/icons'],
          query: ['@tanstack/react-query', 'axios', 'dayjs'],
        },
      },
    },
    // Каталог Ant Design весит ~1 МБ в минифицированном виде (333 КБ gzip). Для локальной
    // системы это один неизменяемый vendor-чанк, который браузер кэширует, поэтому порог
    // предупреждения поднят явно.
    chunkSizeWarningLimit: 1200,
  },
});
