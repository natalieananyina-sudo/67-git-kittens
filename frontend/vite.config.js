import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Бэкенд (FastAPI) во время разработки работает на порту 8000.
// Прокси пересылает на него запросы /api, а также документацию API (/docs, /openapi.json),
// поэтому фронтенду не нужно знать адрес бэкенда и не возникает проблем с CORS.
const BACKEND = process.env.BACKEND_URL ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': BACKEND,
      '/docs': BACKEND,
      '/openapi.json': BACKEND,
    },
  },
})
