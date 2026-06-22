import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/chat': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/documents': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/demos': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/history': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/feedback': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/error-logs': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
